import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import {
  createCallIdTracker,
  createProgressAwareRepeatDetector,
  delegationFailureClass,
  delegationTaskKey,
  stableString,
} from "./reliability-core.js"

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..")
const POLICY = JSON.parse(fs.readFileSync(path.join(ROOT, "reliability.json"), "utf8"))
const TERMINAL = new Set(["COMPLETED", "FAILED", "ABORTED", "IDLE", "ERROR"])
const DELEGATION_TOOLS = new Set(["task", "subagent"])
const now = () => Date.now()
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const profileName = () => {
  const name = String(process.env.RELIABILITY_PROFILE || POLICY.default_profile || "normal").toLowerCase()
  return POLICY.profiles?.[name] ? name : POLICY.default_profile || "normal"
}
const defaults = () => POLICY.profiles[profileName()]

const intEnv = (name, fallback, { min = 1 } = {}) => {
  const raw = process.env[name]
  if (raw === undefined || raw === "") return fallback
  const value = Number.parseInt(raw, 10)
  return Number.isFinite(value) && value >= min ? value : fallback
}
const numberEnv = (name, fallback, { min = 0 } = {}) => {
  const raw = process.env[name]
  if (raw === undefined || raw === "") return fallback
  const value = Number(raw)
  return Number.isFinite(value) && value >= min ? value : fallback
}
const normalizeError = (value) =>
  String(value ?? "")
    .toLowerCase()
    .replace(/\b[0-9a-f]{8,}\b/g, "<id>")
    .replace(/\b\d+ms\b/g, "<duration>")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 500)
const eventProps = (event) => event?.properties ?? event?.data ?? {}
const eventSession = (event) => {
  const p = eventProps(event)
  const info = p.info ?? p.session ?? p
  return {
    id: info?.sessionID ?? p.sessionID ?? p.sessionId ?? event?.sessionID ?? info?.id,
    parentID: info?.parentID ?? info?.parentId ?? info?.parent?.id ?? p.parentID ?? p.parentId,
    agent: info?.agent ?? p.agent,
  }
}
const hookSessionID = (input) =>
  input?.sessionID ?? input?.sessionId ?? input?.context?.sessionID ?? input?.context?.sessionId
const nativeCallID = (input) => input?.callID ?? input?.callId ?? input?.toolCallID
const statusName = (value) => {
  if (!value) return "RUNNING"
  if (typeof value === "string") return value.toUpperCase()
  return String(value.type ?? value.status ?? value.state ?? "RUNNING").toUpperCase()
}
const unwrap = (value) => value?.data ?? value

export const ReliabilityV1Plugin = async ({ client }) => {
  const d = defaults()
  const globalParallel = intEnv("MAX_PARALLEL_SUBAGENTS", Number(d.max_parallel_subagents))
  const queueTimeoutMs = intEnv("SUBAGENT_QUEUE_TIMEOUT_SECONDS", Number(d.queue_timeout_seconds)) * 1000
  const stalledMs = intEnv("SUBAGENT_STALLED_TIMEOUT_SECONDS", Number(d.stalled_timeout_seconds)) * 1000
  const maxDurationMs = intEnv("SUBAGENT_MAX_DURATION_SECONDS", Number(d.max_agent_duration_seconds)) * 1000
  const maxSameError = intEnv("MAX_SAME_ERROR", Number(d.max_same_error))
  const maxSubagentRetries = intEnv(
    "MAX_SUBAGENT_RETRIES",
    Number(d.max_subagent_retries ?? d.max_retries ?? 1),
  )
  const watchMs = intEnv("SUBAGENT_WATCH_INTERVAL_SECONDS", Number(d.watch_interval_seconds)) * 1000
  const maxChildCost = numberEnv("MAX_CHILD_COST", Number(d.max_child_cost ?? 0))
  const maxRunCost = numberEnv("MAX_RUN_COST", Number(d.max_run_cost ?? 0))
  const queuePollMs = Math.min(1000, watchMs)

  const sessions = new Map()
  const childrenByParent = new Map()
  const reservations = new Map()
  const sessionAgents = new Map()
  const messageCosts = new Map()
  const inFlightTools = new Map()
  const delegations = new Map()
  const delegationByTaskID = new Map()
  const callIds = createCallIdTracker()
  const repeatDetector = createProgressAwareRepeatDetector()

  const stateFor = (id) => {
    if (!id) return undefined
    if (!sessions.has(id)) {
      sessions.set(id, {
        id,
        parentID: undefined,
        createdAt: now(),
        lastActivityAt: now(),
        lastProgressAt: now(),
        status: "RUNNING",
        waitingPermission: false,
        lastError: "",
        sameErrorCount: 0,
        abortedByWatchdog: false,
        abortReason: undefined,
        cost: 0,
      })
    }
    return sessions.get(id)
  }

  const markStateProgress = (id) => {
    const state = stateFor(id)
    if (!state) return
    state.lastActivityAt = now()
    state.lastProgressAt = now()
    state.sameErrorCount = 0
    state.lastError = ""
  }
  const markProgress = (id) => {
    markStateProgress(id)
    repeatDetector.markProgress(id)
  }

  const delegationForArgs = (parentID, args = {}) => {
    const existingByTask = args?.task_id && delegationByTaskID.get(String(args.task_id))
    if (existingByTask) return existingByTask
    const key = delegationTaskKey({ parentID, args })
    let item = delegations.get(key)
    if (!item) {
      item = {
        key,
        parentID,
        taskID: undefined,
        attempts: 0,
        failures: 0,
        status: "pending",
        lastFailure: "",
      }
      delegations.set(key, item)
    }
    return item
  }

  const prepareDelegation = (parentID, args = {}) => {
    const item = delegationForArgs(parentID, args)
    if (item.status === "running" && !args.task_id) {
      throw new Error(`Reliability guard: equivalent delegated task is already running (${item.key}).`)
    }
    if (item.status === "failed" || item.failures > maxSubagentRetries) {
      throw new Error(
        `Reliability guard: subagent retry budget exhausted for ${item.key} after ${item.failures} failure(s).`,
      )
    }
    if (item.status === "retryable_failed" && item.taskID && !args.task_id) {
      args.task_id = item.taskID
    }
    if (args.task_id) {
      item.taskID = String(args.task_id)
      delegationByTaskID.set(item.taskID, item)
      const child = stateFor(item.taskID)
      if (child) {
        child.abortedByWatchdog = false
        child.abortReason = undefined
        child.status = "RUNNING"
        child.createdAt = now()
        markProgress(child.id)
      }
    }
    item.attempts += 1
    item.status = "running"
    return item
  }

  const recordDelegationOutcome = (parentID, part) => {
    if (!part || part.type !== "tool" || !DELEGATION_TOOLS.has(part.tool)) return
    const toolState = part.state
    if (!toolState || !["completed", "error"].includes(toolState.status)) return
    const args = toolState.input ?? {}
    const taskID =
      toolState.metadata?.sessionId ??
      toolState.metadata?.sessionID ??
      toolState.metadata?.task_id ??
      args?.task_id
    const item = delegationForArgs(parentID, taskID ? { ...args, task_id: taskID } : args)
    if (taskID) {
      item.taskID = String(taskID)
      delegationByTaskID.set(item.taskID, item)
    }
    if (toolState.status === "completed") {
      item.status = "complete"
      item.lastFailure = ""
    } else {
      const reason = normalizeError(toolState.error)
      item.failures += 1
      item.lastFailure = reason
      item.status =
        delegationFailureClass(reason) === "retryable" && item.failures <= maxSubagentRetries
          ? "retryable_failed"
          : "failed"
    }
    // Receiving a child terminal outcome is material progress for the parent,
    // including cancellation/failure. It must get a fresh supervision window.
    markProgress(parentID)
  }

  function consumeOldestReservation(parentID, childID) {
    let selected
    for (const [callID, reservation] of reservations.entries()) {
      if (reservation.parentID !== parentID) continue
      if (!selected || reservation.createdAt < selected[1].createdAt) selected = [callID, reservation]
    }
    if (!selected) return
    reservations.delete(selected[0])
    const item = selected[1].taskKey && delegations.get(selected[1].taskKey)
    if (item && childID) {
      item.taskID = childID
      delegationByTaskID.set(childID, item)
    }
  }

  const registerChild = (id, parentID, status) => {
    if (!id || !parentID) return false
    const previous = sessions.get(id)
    const wasKnown = Boolean(previous?.parentID === parentID)
    const state = stateFor(id)
    state.parentID = parentID
    if (status) state.status = statusName(status)
    if (!childrenByParent.has(parentID)) childrenByParent.set(parentID, new Set())
    childrenByParent.get(parentID).add(id)
    if (!wasKnown) consumeOldestReservation(parentID, id)
    return !wasKnown
  }

  const activeChildren = (parentID) => {
    const ids = childrenByParent.get(parentID) ?? new Set()
    return [...ids]
      .map((id) => sessions.get(id))
      .filter((state) => state && !TERMINAL.has(statusName(state.status)) && !state.abortedByWatchdog)
  }
  const reservationCount = (parentID) =>
    [...reservations.values()].filter((reservation) => reservation.parentID === parentID).length
  const maxParallelFor = (parentID) => {
    const agent = sessionAgents.get(parentID)
    const envName = agent && POLICY.lead_parallel_env?.[agent]
    return envName ? intEnv(envName, globalParallel) : globalParallel
  }
  const usedSlots = (parentID) => activeChildren(parentID).length + reservationCount(parentID)
  const hasDelegatedChildren = (parentID) => (childrenByParent.get(parentID)?.size ?? 0) > 0

  const reconcileChildren = async (parentID) => {
    try {
      const children = unwrap(await client.session.children({ path: { id: parentID } })) ?? []
      for (const child of children) {
        const id = child?.id ?? child?.sessionID
        if (id) registerChild(id, child?.parentID ?? child?.parentId ?? parentID, child?.status)
      }
    } catch {
      // Event-driven state remains authoritative when the endpoint is unavailable.
    }
  }

  const acquireSlot = async (parentID, callID, taskKey) => {
    const startedAt = now()
    while (true) {
      await reconcileChildren(parentID)
      const limit = maxParallelFor(parentID)
      if (usedSlots(parentID) < limit) {
        reservations.set(callID, { parentID, createdAt: now(), taskKey })
        return
      }
      if (now() - startedAt >= queueTimeoutMs) {
        throw new Error(
          `Reliability guard: subagent queue timed out after ${Math.floor(queueTimeoutMs / 1000)}s while waiting for one of ${limit} slots.`,
        )
      }
      await sleep(queuePollMs)
    }
  }

  const stateDirectory = () => {
    if (process.env.RELIABILITY_STATE_DIR) return process.env.RELIABILITY_STATE_DIR
    const base = process.env.XDG_STATE_HOME || path.join(process.env.HOME || ".", ".local", "state")
    return path.join(base, "opencode-agent-toolkit", "runs")
  }
  const writeCheckpoint = (state) => {
    if (!state?.id) return
    try {
      const dir = stateDirectory()
      fs.mkdirSync(dir, { recursive: true })
      const delegation = delegationByTaskID.get(state.id)
      const payload = {
        sessionID: state.id,
        parentID: state.parentID,
        agent: sessionAgents.get(state.id),
        status: statusName(state.status),
        abortReason: state.abortReason,
        delegation: delegation
          ? {
              key: delegation.key,
              attempts: delegation.attempts,
              failures: delegation.failures,
              status: delegation.status,
              lastFailure: delegation.lastFailure,
            }
          : undefined,
        providerReportedCost: state.cost,
        startedAt: new Date(state.createdAt).toISOString(),
        lastActivityAt: new Date(state.lastActivityAt).toISOString(),
        lastProgressAt: new Date(state.lastProgressAt).toISOString(),
      }
      const target = path.join(dir, `${state.id}.json`)
      const temp = `${target}.tmp-${process.pid}`
      fs.writeFileSync(temp, JSON.stringify(payload, null, 2) + "\n")
      fs.renameSync(temp, target)
    } catch {
      // Checkpoint persistence must never crash the OpenCode runtime.
    }
  }

  const abortSession = async (state, reason) => {
    if (!state || state.abortedByWatchdog || TERMINAL.has(statusName(state.status))) return
    state.abortedByWatchdog = true
    state.abortReason = reason
    state.status = "ABORTED"
    writeCheckpoint(state)
    try {
      await client.session.abort({ path: { id: state.id } })
      await client.app.log({
        body: {
          service: "agent-reliability",
          level: "warn",
          message: `watchdog aborted session ${state.id}: ${reason}`,
          extra: { sessionID: state.id, reason },
        },
      })
    } catch {
      // The session may already have become terminal.
    }
  }

  const rootID = (id) => {
    let current = id
    const seen = new Set()
    while (current && !seen.has(current)) {
      seen.add(current)
      const parent = sessions.get(current)?.parentID
      if (!parent) return current
      current = parent
    }
    return id
  }
  const updateMessageCost = (event) => {
    const p = eventProps(event)
    const info = p.info ?? p.message ?? p
    if (info?.role !== "assistant" || typeof info?.cost !== "number") return
    const sessionID = info?.sessionID ?? p.sessionID
    const messageID = info?.id ?? info?.messageID
    if (!sessionID || !messageID) return
    messageCosts.set(`${sessionID}:${messageID}`, Math.max(0, info.cost))
    let total = 0
    for (const [key, cost] of messageCosts.entries()) if (key.startsWith(`${sessionID}:`)) total += cost
    stateFor(sessionID).cost = total
  }
  const enforceCostBudgets = async (sessionID) => {
    if (!sessionID) return
    const state = stateFor(sessionID)
    if (state?.parentID && maxChildCost > 0 && state.cost > maxChildCost) {
      await abortSession(state, `child provider-reported cost exceeded (${state.cost.toFixed(4)} > ${maxChildCost})`)
    }
    if (maxRunCost <= 0) return
    const root = rootID(sessionID)
    const family = [...sessions.values()].filter((candidate) => rootID(candidate.id) === root)
    const total = family.reduce((sum, candidate) => sum + (candidate.cost || 0), 0)
    if (total <= maxRunCost) return
    for (const candidate of family) {
      await abortSession(candidate, `run provider-reported cost exceeded (${total.toFixed(4)} > ${maxRunCost})`)
    }
  }
  const recordFailure = async (sessionID, value) => {
    const state = stateFor(sessionID)
    if (!state) return
    const signature = normalizeError(value)
    state.lastActivityAt = now()
    if (signature && signature === state.lastError) state.sameErrorCount += 1
    else {
      state.lastError = signature
      state.sameErrorCount = 1
    }
    const fatalProvider = /\b(400|401|403|404)\b|unauth|forbidden|invalid[ -]?request|model.+not found|credential/i.test(signature)
    if (state.parentID && fatalProvider) {
      await abortSession(state, `non-retryable provider/configuration failure: ${signature}`)
    } else if (state.parentID && state.sameErrorCount >= maxSameError) {
      await abortSession(state, `same failure repeated ${state.sameErrorCount} times`)
    }
  }

  const timer = setInterval(async () => {
    const ts = now()
    for (const [callID, reservation] of reservations.entries()) {
      if (ts - reservation.createdAt > queueTimeoutMs) reservations.delete(callID)
    }
    for (const state of sessions.values()) {
      if (!state.parentID || TERMINAL.has(statusName(state.status)) || state.abortedByWatchdog || state.waitingPermission) continue

      // A lead waiting for an active child is healthy supervision, not a stall.
      // The leaf has its own watchdog. Killing the parent here would discard
      // completed sibling handoffs and force the whole council to restart.
      if (usedSlots(state.id) > 0) {
        state.lastActivityAt = ts
        continue
      }

      if (maxChildCost > 0 && state.cost > maxChildCost) {
        await abortSession(state, `child provider-reported cost exceeded (${state.cost.toFixed(4)} > ${maxChildCost})`)
        continue
      }
      // Absolute child duration remains useful for leaves. Leads that have
      // delegated children are bounded by step caps + stall detection instead,
      // so long-running councils are not killed immediately after a child ends.
      if (!hasDelegatedChildren(state.id) && ts - state.createdAt > maxDurationMs) {
        await abortSession(state, "max-duration-exceeded")
        continue
      }
      if (ts - state.lastProgressAt > stalledMs) await abortSession(state, "no-material-progress")
    }
  }, watchMs)
  timer.unref?.()

  return {
    "chat.message": async (input) => {
      const sessionID = hookSessionID(input)
      if (sessionID && input?.agent) sessionAgents.set(sessionID, input.agent)
      if (sessionID) stateFor(sessionID).lastActivityAt = now()
    },
    "chat.params": async (input) => {
      const sessionID = hookSessionID(input)
      if (sessionID && input?.agent) sessionAgents.set(sessionID, input.agent)
      if (sessionID) stateFor(sessionID).lastActivityAt = now()
    },
    event: async ({ event }) => {
      const type = event?.type
      const { id, parentID, agent } = eventSession(event)
      const state = stateFor(id)
      if (!state) return
      if (agent) sessionAgents.set(id, agent)
      if (parentID) registerChild(id, parentID, eventProps(event)?.status)
      if (["message.updated", "message.part.updated", "tool.execute.before", "tool.execute.after", "todo.updated", "session.updated", "session.status"].includes(type)) {
        state.lastActivityAt = now()
      }
      if (["file.edited", "session.diff", "todo.updated"].includes(type)) markProgress(id)
      if (type === "message.part.updated") recordDelegationOutcome(id, eventProps(event).part)
      if (type === "permission.asked") {
        state.waitingPermission = true
        state.status = "WAITING_PERMISSION"
      }
      if (type === "permission.replied") {
        state.waitingPermission = false
        state.status = "RUNNING"
        markProgress(id)
      }
      if (type === "session.idle") {
        state.status = "COMPLETED"
        markProgress(id)
        writeCheckpoint(state)
      }
      if (type === "session.status") state.status = statusName(eventProps(event).status)
      if (type === "message.updated") {
        const p = eventProps(event)
        const info = p.info ?? p.message ?? p
        if (info?.agent) sessionAgents.set(id, info.agent)
        updateMessageCost(event)
        await enforceCostBudgets(id)
      }
      if (type === "session.error") {
        state.status = "FAILED"
        const p = eventProps(event)
        await recordFailure(id, p.error?.message ?? p.error ?? p.message)
        writeCheckpoint(state)
      }
    },
    "tool.execute.before": async (input, output) => {
      const sessionID = hookSessionID(input)
      if (!sessionID) return
      const state = stateFor(sessionID)
      state.lastActivityAt = now()
      const args = output?.args ?? input?.args ?? {}
      const callID = callIds.begin({
        nativeID: nativeCallID(input),
        sessionID,
        tool: input?.tool,
        args: input?.args,
      })
      if (DELEGATION_TOOLS.has(input?.tool)) {
        const delegation = prepareDelegation(sessionID, args)
        markProgress(sessionID)
        await acquireSlot(sessionID, callID, delegation.key)
      }
      inFlightTools.set(callID, { sessionID, tool: input?.tool, args: stableString(args) })
    },
    "tool.execute.after": async (input, output) => {
      const sessionID = hookSessionID(input)
      if (!sessionID) return
      const callID = callIds.end({
        nativeID: nativeCallID(input),
        sessionID,
        tool: input?.tool,
        args: input?.args,
      })
      if (DELEGATION_TOOLS.has(input?.tool)) reservations.delete(callID)
      const state = stateFor(sessionID)
      state.lastActivityAt = now()
      const failed = Boolean(output?.error ?? output?.status === "error")
      if (failed) await recordFailure(sessionID, output?.error?.message ?? output?.error ?? output)

      const before = inFlightTools.get(callID) ?? {
        sessionID,
        tool: input?.tool,
        args: stableString(input?.args),
      }
      const result = normalizeError(output?.output ?? output?.result ?? output?.metadata ?? output?.error ?? output)
      const { same, count } = repeatDetector.observe({
        sessionID,
        tool: before.tool,
        args: before.args,
        result,
        failed,
      })
      inFlightTools.delete(callID)
      if (DELEGATION_TOOLS.has(input?.tool)) markProgress(sessionID)
      else if (!failed && !same) markStateProgress(sessionID)
      if (state.parentID && same && count >= maxSameError) {
        await abortSession(state, `same tool call produced the same result ${count} times`)
      }
    },
  }
}
