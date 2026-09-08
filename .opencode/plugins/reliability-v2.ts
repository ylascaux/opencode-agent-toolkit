import { Plugin } from "@opencode/plugin"

const intEnv = (name: string, fallback: number) => {
  const raw = process.env[name]
  if (!raw) return fallback
  const value = Number.parseInt(raw, 10)
  return Number.isFinite(value) && value > 0 ? value : fallback
}

const terminalStatuses = new Set(["COMPLETED", "FAILED", "ABORTED"])
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export default Plugin.define({
  id: "agent-reliability",
  async setup(ctx) {
    const maxParallel = intEnv("MAX_PARALLEL_SUBAGENTS", 3)
    const queueTimeoutMs = intEnv("SUBAGENT_QUEUE_TIMEOUT_SECONDS", 600) * 1000
    const stalledMs = intEnv("SUBAGENT_STALLED_TIMEOUT_SECONDS", 180) * 1000
    const maxDurationMs = intEnv("SUBAGENT_MAX_DURATION_SECONDS", 900) * 1000
    const watchMs = intEnv("SUBAGENT_WATCH_INTERVAL_SECONDS", 15) * 1000
    const maxRetries = intEnv("MAX_PROVIDER_RETRIES", 2)
    const queuePollMs = Math.min(1000, watchMs)

    type State = {
      id: string
      parentID?: string
      createdAt: number
      lastActivityAt: number
      lastProgressAt: number
      status: string
      waitingPermission: boolean
      aborted: boolean
    }

    const states = new Map<string, State>()
    const children = new Map<string, Set<string>>()
    const pending = new Map<string, number>()
    const now = () => Date.now()

    const ensure = (id?: string) => {
      if (!id) return undefined
      let state = states.get(id)
      if (!state) {
        state = {
          id,
          createdAt: now(),
          lastActivityAt: now(),
          lastProgressAt: now(),
          status: "RUNNING",
          waitingPermission: false,
          aborted: false,
        }
        states.set(id, state)
      }
      return state
    }

    const details = (event: any) => event?.properties ?? event?.data ?? event ?? {}
    const sessionInfo = (event: any) => {
      const d = details(event)
      const info = d.info ?? d.session ?? d
      return {
        id: info?.id ?? d.sessionID ?? d.sessionId ?? event?.sessionID,
        parentID: info?.parentID ?? info?.parentId ?? d.parentID ?? d.parentId,
      }
    }

    const activeCount = (parentID: string) => {
      const ids = children.get(parentID) ?? new Set<string>()
      let count = 0
      for (const id of ids) {
        const state = states.get(id)
        if (state && !terminalStatuses.has(state.status)) count += 1
      }
      return count
    }

    const usedSlots = (parentID: string) => activeCount(parentID) + (pending.get(parentID) ?? 0)

    const acquireSlot = async (parentID: string) => {
      const startedAt = now()
      while (usedSlots(parentID) >= maxParallel) {
        if (now() - startedAt >= queueTimeoutMs) {
          throw new Error(
            `Reliability guard: subagent queue timed out after ${Math.floor(queueTimeoutMs / 1000)}s while waiting for one of ${maxParallel} slots.`,
          )
        }
        await sleep(queuePollMs)
      }
      pending.set(parentID, (pending.get(parentID) ?? 0) + 1)
    }

    const releaseSlot = (parentID: string) => {
      const count = pending.get(parentID) ?? 0
      if (count <= 1) pending.delete(parentID)
      else pending.set(parentID, count - 1)
    }

    const abort = async (state: State, reason: string) => {
      if (state.aborted || terminalStatuses.has(state.status)) return
      state.aborted = true
      state.status = "ABORTED"
      try {
        await ctx.session.interrupt({ sessionID: state.id, continue: false })
        console.warn(`[agent-reliability] aborted ${state.id}: ${reason}`)
      } catch (error) {
        console.error(`[agent-reliability] failed to abort ${state.id}: ${String(error)}`)
      }
    }

    const controller = new AbortController()
    void (async () => {
      for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
        const type = (event as any)?.type
        const { id, parentID } = sessionInfo(event)
        const state = ensure(id)
        if (!state) continue

        if (parentID) {
          state.parentID = parentID
          if (!children.has(parentID)) children.set(parentID, new Set())
          children.get(parentID)!.add(state.id)
        }

        if (["message.updated", "message.part.updated", "session.updated", "session.status", "todo.updated"].includes(type)) {
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
        if (type === "session.error") state.status = "FAILED"
      }
    })().catch((error) => {
      if (!controller.signal.aborted) console.error(`[agent-reliability] event loop failed: ${String(error)}`)
    })

    const timer = setInterval(async () => {
      const ts = now()
      for (const state of states.values()) {
        if (!state.parentID || terminalStatuses.has(state.status) || state.waitingPermission) continue
        if (ts - state.createdAt > maxDurationMs) {
          await abort(state, "max-duration-exceeded")
          continue
        }
        if (ts - state.lastProgressAt > stalledMs) await abort(state, "no-material-progress")
      }
    }, watchMs)
    timer.unref?.()

    await ctx.tool.hook("execute.before", async (event: any) => {
      if (!["subagent", "task"].includes(event.tool)) return
      const parentID = event.sessionID ?? event.sessionId
      if (!parentID) return
      await acquireSlot(parentID)
    })

    await ctx.tool.hook("execute.after", (event: any) => {
      const parentID = event.sessionID ?? event.sessionId
      if (["subagent", "task"].includes(event.tool) && parentID) releaseSlot(parentID)

      const state = ensure(parentID)
      if (!state) return
      state.lastActivityAt = now()
      if (event.status === "completed") state.lastProgressAt = now()
    })

    await ctx.session.hook("retry", (event) => {
      const status = event.error.status
      if ([400, 401, 403, 404].includes(status ?? 0)) {
        event.decision = { retry: false }
        return
      }
      if (event.attempt > maxRetries + 1) {
        event.decision = { retry: false }
        return
      }
      if (status === 429 || (status !== undefined && status >= 500)) {
        event.decision = { retry: true, delay: Math.min(10_000, 1000 * event.attempt) }
      }
    })

    return () => {
      controller.abort()
      clearInterval(timer)
    }
  },
})
