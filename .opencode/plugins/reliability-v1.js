const intEnv = (name, fallback) => {
  const raw = process.env[name]
  if (!raw) return fallback
  const value = Number.parseInt(raw, 10)
  return Number.isFinite(value) && value > 0 ? value : fallback
}

const now = () => Date.now()

const normalizeError = (value) =>
  String(value ?? "")
    .toLowerCase()
    .replace(/\b[0-9a-f]{8,}\b/g, "<id>")
    .replace(/\b\d+ms\b/g, "<duration>")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 500)

const eventSession = (event) => {
  const p = event?.properties ?? event?.data ?? {}
  const info = p.info ?? p.session ?? p
  return {
    id: info?.id ?? p.sessionID ?? p.sessionId ?? event?.sessionID,
    parentID: info?.parentID ?? info?.parentId ?? p.parentID ?? p.parentId,
  }
}

const hookSessionID = (input) =>
  input?.sessionID ?? input?.sessionId ?? input?.context?.sessionID ?? input?.context?.sessionId

export const ReliabilityV1Plugin = async ({ client }) => {
  const maxParallel = intEnv("MAX_PARALLEL_SUBAGENTS", 3)
  const stalledMs = intEnv("SUBAGENT_STALLED_TIMEOUT_SECONDS", 180) * 1000
  const maxDurationMs = intEnv("SUBAGENT_MAX_DURATION_SECONDS", 900) * 1000
  const maxSameError = intEnv("MAX_SAME_ERROR", 2)
  const watchMs = intEnv("SUBAGENT_WATCH_INTERVAL_SECONDS", 15) * 1000

  const sessions = new Map()
  const childrenByParent = new Map()

  const stateFor = (id) => {
    if (!id) return undefined
    if (!sessions.has(id)) {
      sessions.set(id, {
        id,
        createdAt: now(),
        lastActivityAt: now(),
        lastProgressAt: now(),
        status: "RUNNING",
        waitingPermission: false,
        lastError: "",
        sameErrorCount: 0,
        abortedByWatchdog: false,
      })
    }
    return sessions.get(id)
  }

  const activeChildren = (parentID) => {
    const ids = childrenByParent.get(parentID) ?? new Set()
    return [...ids]
      .map((id) => sessions.get(id))
      .filter((s) => s && !["COMPLETED", "FAILED", "ABORTED"].includes(s.status))
  }

  const abortChild = async (state, reason) => {
    if (!state || state.abortedByWatchdog) return
    state.abortedByWatchdog = true
    state.status = "ABORTED"
    try {
      await client.session.abort({ path: { id: state.id } })
      await client.app.log({
        body: {
          service: "agent-reliability",
          level: "warn",
          message: `watchdog aborted child ${state.id}: ${reason}`,
          extra: { sessionID: state.id, reason },
        },
      })
    } catch (error) {
      await client.app.log({
        body: {
          service: "agent-reliability",
          level: "error",
          message: `failed to abort child ${state.id}`,
          extra: { sessionID: state.id, reason, error: String(error) },
        },
      })
    }
  }

  const timer = setInterval(async () => {
    const ts = now()
    for (const state of sessions.values()) {
      if (!state.parentID || ["COMPLETED", "FAILED", "ABORTED"].includes(state.status)) continue
      if (state.waitingPermission) continue
      if (ts - state.createdAt > maxDurationMs) {
        await abortChild(state, "max-duration-exceeded")
        continue
      }
      if (ts - state.lastProgressAt > stalledMs) {
        await abortChild(state, "no-material-progress")
      }
    }
  }, watchMs)
  timer.unref?.()

  return {
    event: async ({ event }) => {
      const type = event?.type
      const { id, parentID } = eventSession(event)
      const state = stateFor(id)
      if (!state) return

      if (parentID) {
        state.parentID = parentID
        if (!childrenByParent.has(parentID)) childrenByParent.set(parentID, new Set())
        childrenByParent.get(parentID).add(id)
      }

      if (["message.updated", "message.part.updated", "tool.execute.before", "tool.execute.after", "todo.updated", "session.updated", "session.status"].includes(type)) {
        state.lastActivityAt = now()
      }
      if (["file.edited", "session.diff", "todo.updated"].includes(type)) {
        state.lastProgressAt = now()
      }
      if (type === "permission.asked") {
        state.waitingPermission = true
        state.status = "WAITING_PERMISSION"
      }
      if (type === "permission.replied") {
        state.waitingPermission = false
        state.status = "RUNNING"
        state.lastActivityAt = now()
      }
      if (type === "session.idle") {
        state.status = "COMPLETED"
        state.lastProgressAt = now()
      }
      if (type === "session.error") {
        const p = event?.properties ?? event?.data ?? {}
        const normalized = normalizeError(p.error?.message ?? p.error ?? p.message)
        if (normalized && normalized === state.lastError) state.sameErrorCount += 1
        else {
          state.lastError = normalized
          state.sameErrorCount = 1
        }
        if (state.sameErrorCount >= maxSameError) await abortChild(state, "repeated-root-error")
      }
    },

    "tool.execute.before": async (input) => {
      if (!["task", "subagent"].includes(input?.tool)) return
      const parentID = hookSessionID(input)
      if (!parentID) return
      const active = activeChildren(parentID)
      if (active.length >= maxParallel) {
        throw new Error(
          `Reliability guard: max parallel subagents reached (${active.length}/${maxParallel}). Wait for an existing child to finish before delegating another task.`,
        )
      }
    },

    "tool.execute.after": async (input, output) => {
      const id = hookSessionID(input)
      const state = stateFor(id)
      if (!state) return
      state.lastActivityAt = now()
      const failed = output?.error ?? output?.status === "error"
      if (!failed) state.lastProgressAt = now()
      if (failed) {
        const normalized = normalizeError(output?.error?.message ?? output?.error)
        if (normalized && normalized === state.lastError) state.sameErrorCount += 1
        else {
          state.lastError = normalized
          state.sameErrorCount = 1
        }
        if (state.sameErrorCount >= maxSameError && state.parentID) {
          await abortChild(state, "repeated-tool-error")
        }
      }
    },
  }
}
