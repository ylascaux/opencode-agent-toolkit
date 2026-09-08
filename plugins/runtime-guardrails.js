import fs from "node:fs"
import path from "node:path"

const ENABLED = /^(1|true|yes|on)$/i.test(process.env.OPENCODE_TOOLKIT_RUNTIME_GUARDS || "")

const PROFILES = {
  cheap: {
    maxParallel: 2,
    stallSeconds: 120,
    maxAgentSeconds: 420,
    maxSameFailure: 2,
    maxChildCost: 0.25,
    maxRunCost: 1.0,
    queueTimeoutSeconds: 300,
    pollSeconds: 10,
  },
  normal: {
    maxParallel: 3,
    stallSeconds: 180,
    maxAgentSeconds: 600,
    maxSameFailure: 2,
    maxChildCost: 0.5,
    maxRunCost: 2.0,
    queueTimeoutSeconds: 600,
    pollSeconds: 10,
  },
  premium: {
    maxParallel: 4,
    stallSeconds: 240,
    maxAgentSeconds: 900,
    maxSameFailure: 3,
    maxChildCost: 1.5,
    maxRunCost: 5.0,
    queueTimeoutSeconds: 900,
    pollSeconds: 10,
  },
}

const profileName = (process.env.OC_RUNTIME_PROFILE || "normal").toLowerCase()
const profile = PROFILES[profileName] || PROFILES.normal

function numberEnv(name, fallback, { integer = false, min = 0 } = {}) {
  const raw = process.env[name]
  if (raw === undefined || raw === "") return fallback
  const value = Number(raw)
  if (!Number.isFinite(value) || value < min || (integer && !Number.isInteger(value))) return fallback
  return value
}

const cfg = {
  maxParallel: numberEnv("OC_MAX_PARALLEL_SUBAGENTS", profile.maxParallel, { integer: true, min: 1 }),
  stallMs: numberEnv("OC_STALLED_TIMEOUT_SECONDS", profile.stallSeconds, { min: 15 }) * 1000,
  maxAgentMs: numberEnv("OC_MAX_AGENT_DURATION_SECONDS", profile.maxAgentSeconds, { min: 30 }) * 1000,
  maxSameFailure: numberEnv("OC_MAX_SAME_FAILURE", profile.maxSameFailure, { integer: true, min: 1 }),
  maxChildCost: numberEnv("OC_MAX_CHILD_COST", profile.maxChildCost, { min: 0 }),
  maxRunCost: numberEnv("OC_MAX_RUN_COST", profile.maxRunCost, { min: 0 }),
  queueTimeoutMs: numberEnv("OC_SUBAGENT_QUEUE_TIMEOUT_SECONDS", profile.queueTimeoutSeconds, { min: 30 }) * 1000,
  pollMs: numberEnv("OC_WATCHDOG_POLL_SECONDS", profile.pollSeconds, { min: 2 }) * 1000,
}

const leadParallelEnv = {
  "meta-router": "OC_MAX_PARALLEL_META_ROUTER",
  orchestrator: "OC_MAX_PARALLEL_ORCHESTRATOR",
  "review-lead": "OC_MAX_PARALLEL_REVIEW_LEAD",
  "platform-architect": "OC_MAX_PARALLEL_PLATFORM_ARCHITECT",
  "security-lead": "OC_MAX_PARALLEL_SECURITY_LEAD",
}

const sessions = new Map()
const sessionAgents = new Map()
const reservations = new Map()
const messageCosts = new Map()
const lastToolResults = new Map()
let watchdogTimer

function now() {
  return Date.now()
}

function sessionState(id) {
  if (!sessions.has(id)) {
    sessions.set(id, {
      id,
      parentID: undefined,
      startedAt: now(),
      lastActivityAt: now(),
      lastProgressAt: now(),
      status: "unknown",
      waitingPermission: false,
      sameFailureCount: 0,
      lastFailure: "",
      cost: 0,
      aborted: false,
      abortReason: undefined,
    })
  }
  return sessions.get(id)
}

function normalize(value) {
  if (value === undefined || value === null) return undefined
  return String(value)
}

function eventProperties(event) {
  return event?.properties || event?.data || {}
}

function eventSessionID(event) {
  const p = eventProperties(event)
  return normalize(p.sessionID || p.info?.sessionID || p.info?.id || p.id)
}

function parentFromInfo(info) {
  return normalize(info?.parentID || info?.parentId || info?.parent?.id)
}

function statusName(status) {
  if (!status) return "unknown"
  if (typeof status === "string") return status.toLowerCase()
  return String(status.type || status.status || status.state || "unknown").toLowerCase()
}

function unwrap(result) {
  return result?.data ?? result
}

function stableString(value) {
  try {
    return JSON.stringify(value, Object.keys(value || {}).sort())
  } catch {
    return String(value)
  }
}

function rootID(id) {
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

function isTerminal(state) {
  return ["idle", "error", "failed", "aborted", "complete", "completed"].includes(state.status)
}

function isChild(state) {
  return Boolean(state.parentID)
}

function maxParallelFor(sessionID) {
  const agent = sessionAgents.get(sessionID)
  const envName = agent && leadParallelEnv[agent]
  return envName ? numberEnv(envName, cfg.maxParallel, { integer: true, min: 1 }) : cfg.maxParallel
}

function activeChildCount(parentID) {
  let count = 0
  for (const state of sessions.values()) {
    if (state.parentID === parentID && !isTerminal(state) && !state.aborted) count += 1
  }
  const cutoff = now() - cfg.maxAgentMs
  for (const reservation of reservations.values()) {
    if (reservation.parentID === parentID && reservation.createdAt >= cutoff) count += 1
  }
  return count
}

async function reconcileChildren(client, parentID) {
  try {
    const children = unwrap(await client.session.children({ path: { id: parentID } })) || []
    for (const child of children) {
      const id = normalize(child?.id || child?.sessionID)
      if (!id) continue
      const state = sessionState(id)
      state.parentID = parentFromInfo(child) || parentID
      const discoveredStatus = statusName(child?.status)
      if (discoveredStatus !== "unknown") state.status = discoveredStatus
    }
  } catch {
    // Event-driven state remains authoritative when the SDK endpoint is unavailable.
  }
}

function stateDirectory() {
  const base = process.env.OC_RUNTIME_STATE_DIR || path.join(process.env.XDG_STATE_HOME || path.join(process.env.HOME || ".", ".local", "state"), "opencode-agent-toolkit")
  return path.join(base, "runs")
}

function writeCheckpoint(state) {
  try {
    const dir = stateDirectory()
    fs.mkdirSync(dir, { recursive: true })
    const payload = {
      sessionID: state.id,
      parentID: state.parentID,
      agent: sessionAgents.get(state.id),
      status: state.status,
      abortReason: state.abortReason,
      cost: state.cost,
      startedAt: new Date(state.startedAt).toISOString(),
      lastActivityAt: new Date(state.lastActivityAt).toISOString(),
      lastProgressAt: new Date(state.lastProgressAt).toISOString(),
    }
    fs.writeFileSync(path.join(dir, `${state.id}.json`), JSON.stringify(payload, null, 2) + "\n")
  } catch {
    // Guardrails must never crash OpenCode because checkpoint persistence failed.
  }
}

async function abortSession(client, state, reason) {
  if (state.aborted || isTerminal(state)) return
  state.aborted = true
  state.abortReason = reason
  state.status = "aborted"
  writeCheckpoint(state)
  try {
    await client.session.abort({ path: { id: state.id } })
  } catch {
    // The session may already have become terminal.
  }
}

function markActivity(id) {
  if (!id) return
  sessionState(id).lastActivityAt = now()
}

function markProgress(id) {
  if (!id) return
  const state = sessionState(id)
  state.lastActivityAt = now()
  state.lastProgressAt = now()
  state.sameFailureCount = 0
  state.lastFailure = ""
}

function failureSignature(value) {
  const text = typeof value === "string" ? value : stableString(value)
  return text.replace(/\s+/g, " ").replace(/[0-9a-f]{8,}/gi, "<id>").slice(0, 500)
}

async function recordFailure(client, sessionID, value) {
  if (!sessionID) return
  const state = sessionState(sessionID)
  const signature = failureSignature(value)
  state.lastActivityAt = now()
  if (signature && signature === state.lastFailure) state.sameFailureCount += 1
  else {
    state.lastFailure = signature
    state.sameFailureCount = 1
  }

  const fatalProvider = /\b(400|401|403|404)\b|unauth|forbidden|invalid[ -]?request|model.+not found|credential/i.test(signature)
  if (isChild(state) && fatalProvider) await abortSession(client, state, `non-retryable provider/configuration failure: ${signature}`)
  else if (isChild(state) && state.sameFailureCount >= cfg.maxSameFailure) await abortSession(client, state, `same failure repeated ${state.sameFailureCount} times`)
}

function updateMessageCost(event) {
  const p = eventProperties(event)
  const info = p.info || p.message || p
  if (info?.role !== "assistant" || typeof info?.cost !== "number") return
  const sessionID = normalize(info.sessionID || p.sessionID)
  const messageID = normalize(info.id || info.messageID)
  if (!sessionID || !messageID) return
  const key = `${sessionID}:${messageID}`
  messageCosts.set(key, Math.max(0, info.cost))
  let total = 0
  for (const [k, cost] of messageCosts.entries()) if (k.startsWith(`${sessionID}:`)) total += cost
  sessionState(sessionID).cost = total
}

async function enforceRunCost(client, sessionID) {
  if (cfg.maxRunCost <= 0 || !sessionID) return
  const root = rootID(sessionID)
  let total = 0
  const family = []
  for (const state of sessions.values()) {
    if (rootID(state.id) === root) {
      total += state.cost || 0
      family.push(state)
    }
  }
  if (total <= cfg.maxRunCost) return
  for (const state of family) await abortSession(client, state, `run cost budget exceeded (${total.toFixed(4)} > ${cfg.maxRunCost})`)
}

async function acquireSubagentSlot(client, parentID, callID) {
  const limit = maxParallelFor(parentID)
  const deadline = now() + cfg.queueTimeoutMs
  while (true) {
    await reconcileChildren(client, parentID)
    if (activeChildCount(parentID) < limit) {
      reservations.set(callID, { parentID, createdAt: now() })
      return
    }
    if (now() >= deadline) throw new Error(`Subagent queue timeout: max parallel limit ${limit} reached for session ${parentID}`)
    await new Promise((resolve) => setTimeout(resolve, Math.min(1000, cfg.pollMs)))
  }
}

async function watchdogTick(client) {
  const current = now()
  for (const [callID, reservation] of reservations.entries()) {
    if (current - reservation.createdAt > cfg.maxAgentMs) reservations.delete(callID)
  }

  for (const state of sessions.values()) {
    if (!isChild(state) || isTerminal(state) || state.aborted) continue
    if (state.waitingPermission) continue

    if (cfg.maxChildCost > 0 && state.cost > cfg.maxChildCost) {
      await abortSession(client, state, `child cost budget exceeded (${state.cost.toFixed(4)} > ${cfg.maxChildCost})`)
      continue
    }
    if (current - state.startedAt > cfg.maxAgentMs) {
      await abortSession(client, state, `child duration exceeded ${Math.round(cfg.maxAgentMs / 1000)}s`)
      continue
    }
    if (current - state.lastProgressAt > cfg.stallMs) {
      await abortSession(client, state, `no progress for ${Math.round((current - state.lastProgressAt) / 1000)}s`)
    }
  }
}

export const RuntimeGuardrailsPlugin = async ({ client }) => {
  if (!ENABLED) return {}

  watchdogTimer = setInterval(() => {
    watchdogTick(client).catch(() => {})
  }, cfg.pollMs)
  watchdogTimer.unref?.()

  return {
    dispose: async () => {
      if (watchdogTimer) clearInterval(watchdogTimer)
      for (const state of sessions.values()) writeCheckpoint(state)
    },

    "chat.message": async (input) => {
      if (input?.sessionID && input?.agent) sessionAgents.set(input.sessionID, input.agent)
      markActivity(input?.sessionID)
    },

    "chat.params": async (input) => {
      if (input?.sessionID && input?.agent) sessionAgents.set(input.sessionID, input.agent)
      markActivity(input?.sessionID)
    },

    "tool.execute.before": async (input, output) => {
      markActivity(input.sessionID)
      if (input.tool === "task" || input.tool === "subagent") {
        await acquireSubagentSlot(client, input.sessionID, input.callID)
      }

      const key = `${input.sessionID}:${input.tool}`
      const signature = stableString(output?.args)
      const previous = lastToolResults.get(key)
      if (previous?.args === signature) previous.repeatedArgs += 1
      else lastToolResults.set(key, { args: signature, result: undefined, repeatedArgs: 1, repeatedResult: 0 })
    },

    "tool.execute.after": async (input, output) => {
      markActivity(input.sessionID)
      if (input.tool === "task" || input.tool === "subagent") reservations.delete(input.callID)

      const key = `${input.sessionID}:${input.tool}`
      const record = lastToolResults.get(key) || { args: stableString(input.args), repeatedArgs: 1, repeatedResult: 0 }
      const resultSignature = failureSignature(output?.output || output?.metadata || "")
      if (record.result === resultSignature && resultSignature) record.repeatedResult += 1
      else {
        record.result = resultSignature
        record.repeatedResult = 1
        markProgress(input.sessionID)
      }
      lastToolResults.set(key, record)

      const state = sessionState(input.sessionID)
      if (isChild(state) && record.repeatedArgs >= cfg.maxSameFailure && record.repeatedResult >= cfg.maxSameFailure) {
        await abortSession(client, state, `repeated tool call produced the same result ${record.repeatedResult} times`)
      }
    },

    event: async ({ event }) => {
      const type = event?.type || ""
      const p = eventProperties(event)
      const sessionID = eventSessionID(event)

      if (type === "session.created") {
        const info = p.info || p.session || p
        const id = normalize(info?.id || info?.sessionID || sessionID)
        if (id) {
          const state = sessionState(id)
          state.parentID = parentFromInfo(info) || state.parentID
          state.startedAt = now()
          state.lastActivityAt = now()
          state.lastProgressAt = now()
          state.status = "active"
        }
        return
      }

      if (type === "session.status" && sessionID) {
        const state = sessionState(sessionID)
        state.status = statusName(p.status)
        state.lastActivityAt = now()
        if (state.status === "idle") {
          state.lastProgressAt = now()
          writeCheckpoint(state)
        }
        return
      }

      if (type === "session.idle" && sessionID) {
        const state = sessionState(sessionID)
        state.status = "idle"
        markProgress(sessionID)
        writeCheckpoint(state)
        return
      }

      if (type === "permission.asked" && sessionID) {
        const state = sessionState(sessionID)
        state.waitingPermission = true
        state.lastActivityAt = now()
        return
      }

      if (type === "permission.replied" && sessionID) {
        const state = sessionState(sessionID)
        state.waitingPermission = false
        markProgress(sessionID)
        return
      }

      if (["file.edited", "session.diff", "todo.updated"].includes(type) && sessionID) {
        markProgress(sessionID)
        return
      }

      if (type === "message.updated") {
        updateMessageCost(event)
        if (sessionID) {
          markActivity(sessionID)
          await enforceRunCost(client, sessionID)
        }
        return
      }

      if (type === "session.error" && sessionID) {
        sessionState(sessionID).status = "error"
        await recordFailure(client, sessionID, p.error || p)
        writeCheckpoint(sessionState(sessionID))
        return
      }

      if (sessionID) markActivity(sessionID)
    },
  }
}

export default RuntimeGuardrailsPlugin
