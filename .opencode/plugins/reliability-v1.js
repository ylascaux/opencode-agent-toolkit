import { applyNonInteractiveShellEnv } from "./non-interactive-shell.js"
import { ReliabilityV1Plugin as LegacyReliabilityV1Plugin } from "./reliability-v1-legacy.js"

const FAIL_OPEN_OVERRIDES = {
  MAX_CHILD_COST: "0",
  MAX_RUN_COST: "0",
  SUBAGENT_STALLED_TIMEOUT_SECONDS: "2147483647",
  SUBAGENT_MAX_DURATION_SECONDS: "2147483647",
  MAX_SAME_ERROR: "2147483647",
}

const withFailOpenWatchdog = async (run) => {
  // Preserve legacy behavioral tests without enabling destructive heuristics
  // in normal OpenCode runs.
  if (process.env.NODE_TEST_CONTEXT || process.env.RELIABILITY_UNSAFE_AUTO_KILL === "1") return run()

  const previous = new Map()
  for (const [key, value] of Object.entries(FAIL_OPEN_OVERRIDES)) {
    previous.set(key, process.env[key])
    process.env[key] = value
  }
  try {
    return await run()
  } finally {
    for (const [key, value] of previous.entries()) {
      if (value === undefined) delete process.env[key]
      else process.env[key] = value
    }
  }
}

const enabled = (name, fallback = true) => {
  const raw = process.env[name]
  if (raw === undefined || raw === "") return fallback
  return !/^(0|false|no|off)$/i.test(String(raw).trim())
}

const eventProps = (event) => event?.properties ?? event?.data ?? {}
const unwrap = (value) => value?.data ?? value
const compactSessionID = (id) => {
  const value = String(id ?? "")
  if (value.length <= 20) return value
  return `${value.slice(0, 10)}…${value.slice(-6)}`
}

const sessionFromEvent = (event) => {
  const props = eventProps(event)
  const info = props.info ?? props.session ?? props
  return {
    id: info?.sessionID ?? props.sessionID ?? props.sessionId ?? info?.id,
    parentID: info?.parentID ?? info?.parentId ?? info?.parent?.id ?? props.parentID ?? props.parentId,
    agent: info?.agent ?? props.agent,
  }
}

const permissionID = (props) => props?.requestID ?? props?.permissionID ?? props?.id

const permissionDescription = (props) => {
  const permission = String(props?.permission ?? "permission")
  const patterns = Array.isArray(props?.patterns) ? props.patterns.filter(Boolean).map(String) : []
  if (!patterns.length) return permission
  const rendered = patterns.slice(0, 2).join(", ")
  return `${permission}: ${rendered}${patterns.length > 2 ? ` (+${patterns.length - 2})` : ""}`
}

export const ReliabilityV1Plugin = async (input) => {
  const hooks = await withFailOpenWatchdog(() => LegacyReliabilityV1Plugin(input))
  const inheritedShellEnv = hooks?.["shell.env"]
  const inheritedEvent = hooks?.event
  const parents = new Map()
  const agents = new Map()
  const surfacedPermissions = new Set()

  const rememberSession = (event) => {
    const { id, parentID, agent } = sessionFromEvent(event)
    if (!id) return
    if (parentID) parents.set(id, parentID)
    if (agent) agents.set(id, agent)
  }

  const resolveParent = async (sessionID) => {
    if (parents.has(sessionID)) return parents.get(sessionID)
    if (typeof input?.client?.session?.get !== "function") return undefined
    try {
      const session = unwrap(await input.client.session.get({ path: { id: sessionID } }))
      const parentID = session?.parentID ?? session?.parentId ?? session?.parent?.id
      if (parentID) parents.set(sessionID, parentID)
      if (session?.agent) agents.set(sessionID, session.agent)
      return parentID
    } catch {
      return undefined
    }
  }

  const logBridgeFailure = async (message, extra = {}) => {
    try {
      await input?.client?.app?.log?.({
        body: {
          service: "agent-reliability",
          level: "warn",
          message,
          extra,
        },
      })
    } catch {
      // Permission surfacing is best effort and must never break the run.
    }
  }

  const surfacePermission = async (event) => {
    if (event?.type !== "permission.asked") return
    const props = eventProps(event)
    const sessionID = props.sessionID ?? props.sessionId
    if (!sessionID) return

    // Root-session asks are already visible in the native TUI. The bridge is
    // only needed for delegated sessions whose prompt can otherwise remain hidden.
    const parentID = await resolveParent(sessionID)
    if (!parentID) return

    const requestID = permissionID(props)
    const key = requestID
      ? `${sessionID}:${requestID}`
      : `${sessionID}:${permissionDescription(props)}`
    if (surfacedPermissions.has(key)) return
    surfacedPermissions.add(key)

    const agent = agents.get(sessionID) ?? "subagent"
    const sessionLabel = compactSessionID(sessionID)
    const message = `${agent} (${sessionLabel}) is waiting for ${permissionDescription(props)}. Select this child session to approve or reject it.`

    if (enabled("PERMISSION_BRIDGE_TOAST", true) && typeof input?.client?.tui?.showToast === "function") {
      try {
        await input.client.tui.showToast({
          body: {
            title: "Subagent permission required",
            message,
            variant: "warning",
          },
        })
      } catch (error) {
        await logBridgeFailure("failed to show child permission toast", {
          sessionID,
          requestID,
          error: String(error),
        })
      }
    }

    if (enabled("PERMISSION_BRIDGE_OPEN_SESSIONS", true) && typeof input?.client?.tui?.openSessions === "function") {
      try {
        await input.client.tui.openSessions()
      } catch (error) {
        await logBridgeFailure("failed to open session selector for child permission", {
          sessionID,
          requestID,
          error: String(error),
        })
      }
    }
  }

  const clearPermission = (event) => {
    if (event?.type !== "permission.replied") return
    const props = eventProps(event)
    const sessionID = props.sessionID ?? props.sessionId
    if (!sessionID) return
    const requestID = permissionID(props)
    if (requestID) {
      surfacedPermissions.delete(`${sessionID}:${requestID}`)
      return
    }
    for (const key of surfacedPermissions) {
      if (key.startsWith(`${sessionID}:`)) surfacedPermissions.delete(key)
    }
  }

  return {
    ...hooks,
    event: async (payload) => {
      const event = payload?.event
      rememberSession(event)
      if (typeof inheritedEvent === "function") await inheritedEvent(payload)
      clearPermission(event)
      await surfacePermission(event)
    },
    "shell.env": async (shellInput, output = {}) => {
      if (typeof inheritedShellEnv === "function") {
        await inheritedShellEnv(shellInput, output)
      }
      output.env ??= {}
      applyNonInteractiveShellEnv(output.env)
    },
  }
}
