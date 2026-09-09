import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { Plugin } from "@opencode/plugin"
import {
  createCallIdTracker,
  createProgressAwareRepeatDetector,
  createStallDetector,
  delegationFailureClass,
  delegationTaskKey,
  providerRetryDecision,
  stableString,
} from "./reliability-core.js"

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..")
const POLICY = JSON.parse(fs.readFileSync(path.join(ROOT, "reliability.json"), "utf8"))
const TERMINAL = new Set(["COMPLETED", "FAILED", "ABORTED", "IDLE", "ERROR"])
const DELEGATION_TOOLS = new Set(["subagent", "task"])
const now = () => Date.now()
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const profileName = () => {
  const name = String(process.env.RELIABILITY_PROFILE || POLICY.default_profile || "normal").toLowerCase()
  return POLICY.profiles?.[name] ? name : POLICY.default_profile || "normal"
}
const defaults = () => POLICY.profiles[profileName()]
const intEnv = (name: string, fallback: number, min = 1) => {
  const raw = process.env[name]
  if (raw === undefined || raw === "") return fallback
  const value = Number.parseInt(raw, 10)
  return Number.isFinite(value) && value >= min ? value : fallback
}
const numberEnv = (name: string, fallback: number, min = 0) => {
  const raw = process.env[name]
  if (raw === undefined || raw === "") return fallback
  const value = Number(raw)
  return Number.isFinite(value) && value >= min ? value : fallback
}
const normalize = (value: any) =>
  String(value ?? "")
    .toLowerCase()
    .replace(/\b[0-9a-f]{8,}\b/g, "<id>")
    .replace(/\b\d+ms\b/g, "<duration>")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 500)
const statusName = (value: any) => {
  if (!value) return "RUNNING"
  if (typeof value === "string") return value.toUpperCase()
  return String(value.type ?? value.status ?? value.state ?? "RUNNING").toUpperCase()
}
const unwrap = (value: any) => value?.data ?? value
const hookArgs = (holder: any) => {
  if (!holder) return {}
  if (typeof holder.get === "function") {
    try {
      return holder.get() ?? {}
    } catch {
      // Fall back to the object shape used by earlier V2 beta builds.
    }
  }
  if (holder.value && typeof holder.value === "object") return holder.value
  return holder
}
const setHookTaskID = (holder: any, taskID: string) => {
  if (!holder) return
  if (typeof holder.update === "function") {
    holder.update((args: any) => ({ ...(args ?? {}), task_id: taskID }))
    return
  }
  if (holder.value && typeof holder.value === "object") {
    holder.value.task_id = taskID
    return
  }
  holder.task_id = taskID
}

export default Plugin.define({
  id: "agent-reliability",
  async setup(ctx) {
    const d = defaults()
    const globalParallel = intEnv("MAX_PARALLEL_SUBAGENTS", Number(d.max_parallel_subagents))
    const queueTimeoutMs = intEnv("SUBAGENT_QUEUE_TIMEOUT_SECONDS", Number(d.queue_timeout_seconds)) * 1000
    const heartbeatMs = intEnv("SUBAGENT_HEARTBEAT_TIMEOUT_SECONDS", Number(d.heartbeat_timeout_seconds)) * 1000
    const stalledMs = intEnv("SUBAGENT_STALLED_TIMEOUT_SECONDS", Number(d.stalled_timeout_seconds)) * 1000
    const maxDurationMs = intEnv("SUBAGENT_MAX_DURATION_SECONDS", Number(d.max_agent_duration_seconds)) * 1000
    const watchMs = intEnv("SUBAGENT_WATCH_INTERVAL_SECONDS", Number(d.watch_interval_seconds)) * 1000
    const maxRetries = intEnv("MAX_PROVIDER_RETRIES", Number(d.max_retries))
    const maxSubagentRetries = intEnv(
      "MAX_SUBAGENT_RETRIES",
      Number(d.max_subagent_retries ?? d.max_retries ?? 1),
    )
    const maxSameError = intEnv("MAX_SAME_ERROR", Number(d.max_same_error))
    const maxChildCost = numberEnv("MAX_CHILD_COST", Number(d.max_child_cost ?? 0))
    const maxRunCost = numberEnv("MAX_RUN_COST", Number(d.max_run_cost ?? 0))
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
      abortReason?: string
      lastError: string
      sameErrorCount: number
      cost: number
    }
    type Delegation = {
      key: string
      parentID: string
      taskID?: string
      attempts: number
      failures: number
      status: "pending" | "running" | "complete" | "retryable_failed" | "failed"
      lastFailure: string
    }

    const states = new Map<string, State>()
    const children = new Map<string, Set<string>>()
    const reservations = new Map<string, { parentID: string; createdAt: number; taskKey?: string }>()
    const sessionAgents = new Map<string, string>()
    const messageCosts = new Map<string, number>()
    const inFlightTools = new Map<string, any>()
    const delegations = new Map<string, Delegation>()
    const delegationByTaskID = new Map<string, Delegation>()
    const callIds = createCallIdTracker()
    const repeatDetector = createProgressAwareRepeatDetector()
    const stallDetector = createStallDetector()

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
          lastError: "",
          sameErrorCount: 0,
          cost: 0,
        }
        states.set(id, state)
      }
      return state
    }

    const markStateProgress = (id?: string) => {
      const state = ensure(id)
      if (!state) return
      state.lastActivityAt = now()
      state.lastProgressAt = now()
      state.sameErrorCount = 0
      state.lastError = ""
    }
    const markProgress = (id?: string) => {
      markStateProgress(id)
      repeatDetector.markProgress(id)
    }

    const delegationForArgs = (parentID: string, args: any = {}) => {
      const existingByTask = args?.task_id && delegationByTaskID.get(String(args.task_id))
      if (existingByTask) return existingByTask
      const key = delegationTaskKey({ parentID, args })
      let item = delegations.get(key)
      if (!item) {
        item = {
          key,
          parentID,
          attempts: 0,
          failures: 0,
          status: "pending",
          lastFailure: "",
        }
        delegations.set(key, item)
      }
      return item
    }

    const prepareDelegation = (parentID: string, args: any = {}) => {
      const item = delegationForArgs(parentID, args)
      if (item.status === "running" && !args.task_id) {
        throw new Error(`Reliability guard: equivalent delegated task is already running (${item.key}).`)
      }
      if (item.status === "failed" || item.failures > maxSubagentRetries) {
        throw new Error(
          `Reliability guard: subagent retry budget exhausted for ${item.key} after ${item.failures} failure(s).`,
        )
      }
      const resumeTaskID = item.status === "retryable_failed" && item.taskID && !args.task_id ? item.taskID : undefined
      const effectiveTaskID = String(args.task_id ?? resumeTaskID ?? "")
      if (effectiveTaskID) {
        item.taskID = effectiveTaskID
        delegationByTaskID.set(effectiveTaskID, item)
      }
      item.attempts += 1
      item.status = "running"
      return { item, resumeTaskID }
    }

    const releaseDelegationReservations = (parentID: string, taskKey: string) => {
      for (const [callID, reservation] of reservations.entries()) {
        if (reservation.parentID === parentID && reservation.taskKey === taskKey) reservations.delete(callID)
      }
    }

    const recordDelegationOutcome = (parentID: string, part: any) => {
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
      releaseDelegationReservations(parentID, item.key)
      if (toolState.status === "completed") {
        item.status = "complete"
        item.lastFailure = ""
      } else {
        const reason = normalize(toolState.error)
        item.failures += 1
        item.lastFailure = reason
        item.status =
          delegationFailureClass(reason) === "retryable" && item.failures <= maxSubagentRetries
            ? "retryable_failed"
            : "failed"
      }
      // A child terminal result, including cancellation, is new evidence for
      // the parent and must reset its own stall window.
      markProgress(parentID)
    }

    const consumeOldestReservation = (parentID: string, childID?: string) => {
      let selected: [string, { parentID: string; createdAt: number; taskKey?: string }] | undefined
      for (const entry of reservations.entries()) {
        if (entry[1].parentID !== parentID) continue
        if (!selected || entry[1].createdAt < selected[1].createdAt) selected = entry
      }
      if (!selected) return
      reservations.delete(selected[0])
      const item = selected[1].taskKey && delegations.get(selected[1].taskKey)
      if (item && childID) {
        item.taskID = childID
        delegationByTaskID.set(childID, item)
      }
    }

    const registerChild = (id?: string, parentID?: string, status?: any) => {
      if (!id || !parentID) return
      const previous = states.get(id)
      const wasKnown = Boolean(previous?.parentID === parentID)
      const state = ensure(id)!
      state.parentID = parentID
      if (status) state.status = statusName(status)
      if (!children.has(parentID)) children.set(parentID, new Set())
      children.get(parentID)!.add(id)
      if (!wasKnown) consumeOldestReservation(parentID, id)
    }

    const activeCount = (parentID: string) => {
      let count = 0
      for (const id of children.get(parentID) ?? new Set<string>()) {
        const state = states.get(id)
        if (state && !TERMINAL.has(statusName(state.status)) && !state.aborted) count += 1
      }
      return count
    }
    const reservationCount = (parentID: string) =>
      [...reservations.values()].filter((reservation) => reservation.parentID === parentID).length
    const maxParallelFor = (parentID: string) => {
      const agent = sessionAgents.get(parentID)
      const envName = agent && POLICY.lead_parallel_env?.[agent]
      return envName ? intEnv(envName, globalParallel) : globalParallel
    }
    const usedSlots = (parentID: string) => activeCount(parentID) + reservationCount(parentID)
    const hasDelegatedChildren = (parentID: string) => (children.get(parentID)?.size ?? 0) > 0
    const hasInFlightTool = (sessionID: string) =>
      [...inFlightTools.values()].some((call) => call.sessionID === sessionID)

    const reconcileChildren = async (parentID: string) => {
      const api: any = (ctx as any).session
      if (!api || typeof api.children !== "function") return
      let result: any
      try {
        result = await api.children({ sessionID: parentID })
      } catch {
        try {
          result = await api.children({ path: { id: parentID } })
        } catch {
          return
        }
      }
      for (const child of unwrap(result) ?? []) {
        const id = child?.id ?? child?.sessionID
        registerChild(id, child?.parentID ?? child?.parentId ?? parentID, child?.status)
      }
    }

    const acquireSlot = async (parentID: string, callID: string, taskKey?: string) => {
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
    const writeCheckpoint = (state: State) => {
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
        // Checkpoint failures must never crash the runtime.
      }
    }

    const preserveRetryableDelegation = (state: State, reason: string) => {
      const delegation = delegationByTaskID.get(state.id)
      if (!delegation || delegation.status === "complete" || delegation.status === "failed") return
      if (delegationFailureClass(reason) !== "retryable") return
      delegation.taskID = state.id
      delegation.status = "retryable_failed"
      delegation.lastFailure = normalize(reason)
      delegationByTaskID.set(state.id, delegation)
    }

    const abort = async (state: State, reason: string) => {
      if (state.aborted || TERMINAL.has(statusName(state.status))) return
      preserveRetryableDelegation(state, reason)
      stallDetector.clear(state.id)
      state.aborted = true
      state.abortReason = reason
      state.status = "ABORTED"
      writeCheckpoint(state)
      try {
        await (ctx as any).session.interrupt({ sessionID: state.id, continue: false })
        console.warn(`[agent-reliability] aborted ${state.id}: ${reason}`)
      } catch (error) {
        console.error(`[agent-reliability] failed to abort ${state.id}: ${String(error)}`)
      }
    }

    const rootID = (id: string) => {
      let current = id
      const seen = new Set<string>()
      while (current && !seen.has(current)) {
        seen.add(current)
        const parent = states.get(current)?.parentID
        if (!parent) return current
        current = parent
      }
      return id
    }
    const updateCost = (event: any) => {
      const p = event?.properties ?? event?.data ?? event ?? {}
      const info = p.info ?? p.message ?? p
      if (info?.role !== "assistant" || typeof info?.cost !== "number") return
      const sessionID = info.sessionID ?? p.sessionID
      const messageID = info.id ?? info.messageID
      if (!sessionID || !messageID) return
      messageCosts.set(`${sessionID}:${messageID}`, Math.max(0, info.cost))
      let total = 0
      for (const [key, cost] of messageCosts.entries()) if (key.startsWith(`${sessionID}:`)) total += cost
      ensure(sessionID)!.cost = total
    }
    const enforceCost = async (sessionID: string) => {
      const state = ensure(sessionID)
      if (!state) return
      if (state.parentID && maxChildCost > 0 && state.cost > maxChildCost) {
        await abort(state, `child provider-reported cost exceeded (${state.cost.toFixed(4)} > ${maxChildCost})`)
      }
      if (maxRunCost <= 0) return
      const root = rootID(sessionID)
      const family = [...states.values()].filter((candidate) => rootID(candidate.id) === root)
      const total = family.reduce((sum, candidate) => sum + (candidate.cost || 0), 0)
      if (total <= maxRunCost) return
      for (const candidate of family) {
        await abort(candidate, `run provider-reported cost exceeded (${total.toFixed(4)} > ${maxRunCost})`)
      }
    }
    const recordFailure = async (sessionID: string, value: any) => {
      const state = ensure(sessionID)
      if (!state) return
      const signature = normalize(value)
      state.lastActivityAt = now()
      if (signature && signature === state.lastError) state.sameErrorCount += 1
      else {
        state.lastError = signature
        state.sameErrorCount = 1
      }
      const fatalProvider = /\b(400|401|403|404)\b|unauth|forbidden|invalid[ -]?request|model.+not found|credential/i.test(signature)
      if (state.parentID && fatalProvider) {
        await abort(state, `non-retryable provider/configuration failure: ${signature}`)
      } else if (state.parentID && state.sameErrorCount >= maxSameError) {
        await abort(state, `same failure repeated ${state.sameErrorCount} times`)
      }
    }

    const controller = new AbortController()
    void (async () => {
      for await (const event of (ctx as any).event.subscribe({ signal: controller.signal })) {
        const type = event?.type
        const p = event?.properties ?? event?.data ?? event ?? {}
        const info = p.info ?? p.session ?? p
        const id = info?.sessionID ?? p.sessionID ?? p.sessionId ?? event?.sessionID ?? info?.id
        const parentID = info?.parentID ?? info?.parentId ?? info?.parent?.id ?? p.parentID ?? p.parentId
        const state = ensure(id)
        if (!state) continue
        if (info?.agent ?? p.agent) sessionAgents.set(id, info?.agent ?? p.agent)
        if (parentID) registerChild(id, parentID, p.status)
        if (["message.updated", "message.part.updated", "session.updated", "session.status", "todo.updated"].includes(type)) {
          state.lastActivityAt = now()
        }
        if (["file.edited", "session.diff", "todo.updated"].includes(type)) markProgress(id)
        if (type === "message.part.updated") recordDelegationOutcome(id, p.part)
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
        if (type === "session.status") {
          const nextStatus = statusName(p.status)
          state.status = nextStatus
          if (!TERMINAL.has(nextStatus) && state.aborted) {
            state.aborted = false
            state.abortReason = undefined
            state.createdAt = now()
            markProgress(id)
          }
        }
        if (type === "message.updated") {
          const message = p.info ?? p.message ?? p
          if (message?.agent) sessionAgents.set(id, message.agent)
          updateCost(event)
          await enforceCost(id)
        }
        if (type === "session.error") {
          state.status = "FAILED"
          await recordFailure(id, p.error?.message ?? p.error ?? p.message)
          writeCheckpoint(state)
        }
      }
    })().catch((error) => {
      if (!controller.signal.aborted) console.error(`[agent-reliability] event loop failed: ${String(error)}`)
    })

    const timer = setInterval(async () => {
      const ts = now()
      for (const [callID, reservation] of reservations.entries()) {
        if (ts - reservation.createdAt > queueTimeoutMs) reservations.delete(callID)
      }
      for (const state of states.values()) {
        if (!state.parentID || TERMINAL.has(statusName(state.status)) || state.aborted || state.waitingPermission) continue

        // WAITING_ON_CHILD is healthy supervision. The active leaf is watched
        // independently; aborting the parent here would discard completed
        // sibling results and force the whole orchestration branch to restart.
        if (usedSlots(state.id) > 0) {
          state.lastActivityAt = ts
          stallDetector.clear(state.id)
          continue
        }

        if (maxChildCost > 0 && state.cost > maxChildCost) {
          await abort(state, `child provider-reported cost exceeded (${state.cost.toFixed(4)} > ${maxChildCost})`)
          continue
        }
        if (!hasDelegatedChildren(state.id) && ts - state.createdAt > maxDurationMs) {
          await abort(state, "max-duration-exceeded")
          continue
        }
        const stall = stallDetector.observe({
          sessionID: state.id,
          timestamp: ts,
          lastActivityAt: state.lastActivityAt,
          lastProgressAt: state.lastProgressAt,
          heartbeatMs,
          stalledMs,
          confirmationMs: watchMs,
          busy: hasInFlightTool(state.id),
        })
        if (stall.stalled) await abort(state, "no-material-progress")
      }
    }, watchMs)
    timer.unref?.()

    await (ctx as any).tool.hook("execute.before", async (event: any) => {
      const sessionID = event.sessionID ?? event.sessionId
      if (!sessionID) return
      if (event.agent) sessionAgents.set(sessionID, event.agent)
      ensure(sessionID)!.lastActivityAt = now()
      const originalArgs = hookArgs(event.args)
      const callID = callIds.begin({
        nativeID: event.callID ?? event.callId ?? event.toolCallID,
        sessionID,
        tool: event.tool,
        args: originalArgs,
      })
      let effectiveArgs = originalArgs
      if (DELEGATION_TOOLS.has(event.tool)) {
        const { item, resumeTaskID } = prepareDelegation(sessionID, originalArgs)
        if (resumeTaskID) {
          setHookTaskID(event.args, resumeTaskID)
          effectiveArgs = { ...originalArgs, task_id: resumeTaskID }
        }
        markProgress(sessionID)
        await acquireSlot(sessionID, callID, item.key)
      }
      inFlightTools.set(callID, { sessionID, tool: event.tool, args: stableString(effectiveArgs) })
    })

    await (ctx as any).tool.hook("execute.after", async (event: any) => {
      const sessionID = event.sessionID ?? event.sessionId
      if (!sessionID) return
      const args = hookArgs(event.args)
      const callID = callIds.end({
        nativeID: event.callID ?? event.callId ?? event.toolCallID,
        sessionID,
        tool: event.tool,
        args,
      })
      if (DELEGATION_TOOLS.has(event.tool)) reservations.delete(callID)
      const state = ensure(sessionID)!
      state.lastActivityAt = now()
      const failed = event.status === "error" || Boolean(event.error)
      if (failed) await recordFailure(sessionID, event.error ?? event)
      const before = inFlightTools.get(callID) ?? {
        sessionID,
        tool: event.tool,
        args: stableString(args),
      }
      const result = normalize(event.output ?? event.result ?? event.metadata ?? event.error ?? event)
      const { same, count } = repeatDetector.observe({
        sessionID,
        tool: before.tool,
        args: before.args,
        result,
        failed,
      })
      inFlightTools.delete(callID)
      if (DELEGATION_TOOLS.has(event.tool)) markProgress(sessionID)
      else if (!failed && !same) markStateProgress(sessionID)
      if (state.parentID && same && count >= maxSameError) {
        await abort(state, `same tool call produced the same result ${count} times`)
      }
    })

    await (ctx as any).session.hook("retry", (event: any) => {
      const decision = providerRetryDecision({
        status: event.error?.status,
        attempt: event.attempt,
        maxRetries,
      })
      if (decision) event.decision = decision
    })

    return () => {
      controller.abort()
      clearInterval(timer)
      for (const state of states.values()) writeCheckpoint(state)
    }
  },
})
