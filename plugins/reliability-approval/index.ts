import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { Plugin } from "@opencode/plugin"
import { ReliabilityApproval } from "./rpc.js"

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..")
const POLICY = JSON.parse(fs.readFileSync(path.join(ROOT, "reliability.json"), "utf8"))
const TERMINAL = new Set(["COMPLETED", "FAILED", "ABORTED", "IDLE", "ERROR"])
const now = () => Date.now()

const profileName = () => {
  const name = String(process.env.RELIABILITY_PROFILE || POLICY.default_profile || "normal").toLowerCase()
  return POLICY.profiles?.[name] ? name : POLICY.default_profile || "normal"
}

const intEnv = (name: string, fallback: number, min = 1) => {
  const raw = process.env[name]
  if (raw === undefined || raw === "") return fallback
  const value = Number.parseInt(raw, 10)
  return Number.isFinite(value) && value >= min ? value : fallback
}

const statusName = (value: any) => {
  if (!value) return "RUNNING"
  if (typeof value === "string") return value.toUpperCase()
  return String(value.type ?? value.status ?? value.state ?? "RUNNING").toUpperCase()
}

type State = {
  id: string
  parentID?: string
  agent?: string
  createdAt: number
  lastActivityAt: number
  lastProgressAt: number
  status: string
  waitingPermission: boolean
}

type SuspectReason = "no-observable-progress" | "max-duration"

export default Plugin.define({
  id: "agent-reliability-approval",
  async setup(ctx) {
    const profile = POLICY.profiles[profileName()]
    const heartbeatMs = intEnv(
      "SUBAGENT_HEARTBEAT_TIMEOUT_SECONDS",
      Number(profile.heartbeat_timeout_seconds),
    ) * 1000
    const stalledMs = intEnv(
      "SUBAGENT_STALLED_TIMEOUT_SECONDS",
      Number(profile.stalled_timeout_seconds),
    ) * 1000
    const maxDurationMs = intEnv(
      "SUBAGENT_MAX_DURATION_SECONDS",
      Number(profile.max_agent_duration_seconds),
    ) * 1000
    const watchMs = intEnv(
      "SUBAGENT_WATCH_INTERVAL_SECONDS",
      Number(profile.watch_interval_seconds),
    ) * 1000
    const promptCooldownMs = Math.max(stalledMs, 5 * 60_000)

    const states = new Map<string, State>()
    const inFlight = new Map<string, number>()
    const pending = new Map<string, SuspectReason>()
    const suppressedUntil = new Map<string, number>()
    const lastPromptAt = new Map<string, number>()

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
        }
        states.set(id, state)
      }
      return state
    }

    const touch = (id?: string, progress = false) => {
      const state = ensure(id)
      if (!state) return
      const ts = now()
      state.lastActivityAt = ts
      if (progress) state.lastProgressAt = ts
      // If the runtime becomes observable again, a previously queued approval
      // is stale. A late TUI response must never kill recovered work.
      pending.delete(state.id)
    }

    const registration = await ctx.rpc.register(ReliabilityApproval, {
      decide: async (input: any) => {
        const sessionID = String(input?.sessionID ?? "")
        const action = String(input?.action ?? "")
        const state = states.get(sessionID)
        if (!state) return { status: "unknown" }

        if (!pending.has(sessionID)) return { status: "stale" }
        pending.delete(sessionID)

        if (action === "keep") {
          const ts = now()
          state.lastActivityAt = ts
          state.lastProgressAt = ts
          suppressedUntil.set(sessionID, ts + promptCooldownMs)
          return { status: "kept" }
        }

        if (action !== "kill") return { status: "unknown" }
        await ctx.session.interrupt({ sessionID, continue: false })
        state.status = "ABORTED"
        return { status: "killed" }
      },
    })

    const controller = new AbortController()
    void (async () => {
      for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
        const type = event?.type
        const p: any = event?.properties ?? event?.data ?? event ?? {}
        const info = p.info ?? p.session ?? p
        const id = info?.sessionID ?? p.sessionID ?? p.sessionId ?? (event as any)?.sessionID ?? info?.id
        const parentID = info?.parentID ?? info?.parentId ?? info?.parent?.id ?? p.parentID ?? p.parentId
        const state = ensure(id)
        if (!state) continue

        if (parentID) state.parentID = parentID
        if (info?.agent ?? p.agent) state.agent = info?.agent ?? p.agent

        if (["message.updated", "message.part.updated", "session.updated", "session.status", "todo.updated"].includes(type)) {
          touch(id, false)
        }
        if (["file.edited", "session.diff", "todo.updated"].includes(type)) touch(id, true)

        if (type === "permission.asked") {
          state.waitingPermission = true
          state.status = "WAITING_PERMISSION"
          pending.delete(state.id)
        }
        if (type === "permission.replied") {
          state.waitingPermission = false
          state.status = "RUNNING"
          touch(id, true)
        }
        if (type === "session.status") state.status = statusName(p.status)
        if (type === "session.idle") {
          state.status = "COMPLETED"
          pending.delete(state.id)
        }
        if (type === "session.error") {
          state.status = "FAILED"
          pending.delete(state.id)
        }
      }
    })().catch((error) => {
      if (!controller.signal.aborted) console.error(`[agent-reliability] approval event loop failed: ${String(error)}`)
    })

    await ctx.tool.hook("execute.before", async (event: any) => {
      const sessionID = event.sessionID ?? event.sessionId
      if (!sessionID) return
      touch(sessionID, false)
      inFlight.set(sessionID, (inFlight.get(sessionID) ?? 0) + 1)
    })

    await ctx.tool.hook("execute.after", async (event: any) => {
      const sessionID = event.sessionID ?? event.sessionId
      if (!sessionID) return
      const next = Math.max(0, (inFlight.get(sessionID) ?? 1) - 1)
      if (next === 0) inFlight.delete(sessionID)
      else inFlight.set(sessionID, next)
      touch(sessionID, true)
    })

    const emitSuspect = async (state: State, reason: SuspectReason, ts: number) => {
      if (!state.parentID || pending.has(state.id)) return
      if ((suppressedUntil.get(state.id) ?? 0) > ts) return
      if (ts - (lastPromptAt.get(state.id) ?? 0) < promptCooldownMs) return

      pending.set(state.id, reason)
      lastPromptAt.set(state.id, ts)
      const payload = {
        sessionID: state.id,
        parentID: state.parentID,
        agent: state.agent ?? "unknown",
        reason,
        ageSeconds: Math.max(0, Math.floor((ts - state.createdAt) / 1000)),
        noActivitySeconds: Math.max(0, Math.floor((ts - state.lastActivityAt) / 1000)),
        noProgressSeconds: Math.max(0, Math.floor((ts - state.lastProgressAt) / 1000)),
      }

      console.warn(
        `[agent-reliability] suspected ${state.id}: ${reason}; waiting for explicit user approval before interrupt`,
      )
      try {
        await registration.events.emit("suspected", payload)
      } catch (error) {
        // Fail open: missing/disconnected TUI means no kill, never a fallback interrupt.
        console.warn(`[agent-reliability] could not request approval for ${state.id}: ${String(error)}`)
      }
    }

    const timer = setInterval(() => {
      const ts = now()
      void (async () => {
        for (const state of states.values()) {
          if (!state.parentID || TERMINAL.has(statusName(state.status)) || state.waitingPermission) continue
          if ((inFlight.get(state.id) ?? 0) > 0) continue

          const staleActivity = ts - state.lastActivityAt > heartbeatMs
          const staleProgress = ts - state.lastProgressAt > stalledMs
          if (staleActivity && staleProgress) {
            await emitSuspect(state, "no-observable-progress", ts)
            continue
          }
          if (ts - state.createdAt > maxDurationMs) await emitSuspect(state, "max-duration", ts)
        }
      })().catch((error) => console.error(`[agent-reliability] approval watchdog failed: ${String(error)}`))
    }, watchMs)
    timer.unref?.()

    return () => {
      controller.abort()
      clearInterval(timer)
      const dispose = (registration as any)?.dispose
      if (typeof dispose === "function") void dispose.call(registration)
    }
  },
})
