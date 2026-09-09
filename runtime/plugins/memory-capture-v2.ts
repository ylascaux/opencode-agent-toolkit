import { createHash } from "node:crypto"
import { mkdir, readFile, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { buildPrompt, extractJson, fingerprint, transcriptFromContext, validateCandidates } from "./memory-capture-core.js"

type Candidate = {
  kind: string
  title: string
  statement: string
  rationale?: string
  confidence: string
  suggested_target?: string
  hats?: string[]
}

type StoredCandidate = Candidate & {
  id: string
  fingerprint: string
  created_at: string
  session_id: string
  project_id: string
  project_name: string
  source: "opencode-v2-session-idle"
  extractor_model: string
  occurrences: number
  last_seen_at: string
}

function truthy(value: string | undefined, fallback = false) {
  if (value === undefined || value.trim() === "") return fallback
  return ["1", "true", "yes", "on"].includes(value.trim().toLowerCase())
}

function intEnv(name: string, fallback: number, min: number) {
  const raw = process.env[name]
  if (!raw) return fallback
  const value = Number.parseInt(raw, 10)
  return Number.isFinite(value) && value >= min ? value : fallback
}

function stateRoot() {
  const root = process.env.OAT_MEMORY_CANDIDATE_DIR || path.join(process.env.XDG_STATE_HOME || path.join(os.homedir(), ".local", "state"), "opencode-agent-toolkit", "memory")
  return path.resolve(root)
}

function splitModel(value: string) {
  const index = value.indexOf("/")
  if (index <= 0 || index === value.length - 1) return null
  return { providerID: value.slice(0, index), id: value.slice(index + 1) }
}

async function existingCandidate(root: string, hash: string) {
  for (const bucket of ["candidates", "accepted", "rejected", "promoted"]) {
    const candidatePath = path.join(root, bucket, `${hash}.json`)
    try {
      const data = JSON.parse(await readFile(candidatePath, "utf8"))
      return { bucket, path: candidatePath, data }
    } catch {}
  }
  return null
}

async function generate(ctx: any, sessionID: string, prompt: string, modelValue: string): Promise<string> {
  const model = splitModel(modelValue)
  if (model && typeof ctx.generate?.text === "function") {
    const result = await ctx.generate.text({ model, prompt })
    return typeof result?.text === "string" ? result.text : ""
  }
  if (typeof ctx.session?.generate === "function") {
    const result = await ctx.session.generate({ sessionID, prompt })
    return typeof result?.text === "string" ? result.text : ""
  }
  throw new Error("OpenCode V2 exposes neither ctx.generate.text nor ctx.session.generate")
}

async function projectInfo(ctx: any) {
  const directory = typeof ctx.location?.directory === "string" ? ctx.location.directory : process.cwd()
  const fallback = {
    id: process.env.OAT_MEMORY_PROJECT || "",
    name: path.basename(directory),
  }
  try {
    const toolkitRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..")
    const meta = JSON.parse(await readFile(path.join(toolkitRoot, ".generated", "memory", "meta.json"), "utf8"))
    return {
      id: typeof meta?.project_id === "string" ? meta.project_id : fallback.id,
      name: typeof meta?.project_name === "string" && meta.project_name ? meta.project_name : fallback.name,
    }
  } catch {
    return fallback
  }
}

async function persist(root: string, sessionID: string, projectID: string, projectName: string, model: string, candidates: Candidate[]) {
  const directory = path.join(root, "candidates")
  await mkdir(directory, { recursive: true, mode: 0o700 })
  let created = 0
  for (const candidate of candidates) {
    const hash = fingerprint(projectID, candidate)
    const existing = await existingCandidate(root, hash)
    const now = new Date().toISOString()
    if (existing) {
      if (existing.bucket === "candidates") {
        const updated = {
          ...existing.data,
          occurrences: Math.max(1, Number(existing.data?.occurrences || 1)) + 1,
          last_seen_at: now,
          session_id: sessionID,
        }
        await writeFile(existing.path, JSON.stringify(updated, null, 2) + "\n", { mode: 0o600 })
      }
      continue
    }
    const stored: StoredCandidate = {
      ...candidate,
      id: hash.slice(0, 12),
      fingerprint: hash,
      created_at: now,
      session_id: sessionID,
      project_id: projectID,
      project_name: projectName,
      source: "opencode-v2-session-idle",
      extractor_model: model,
      occurrences: 1,
      last_seen_at: now,
    }
    await writeFile(path.join(directory, `${hash}.json`), JSON.stringify(stored, null, 2) + "\n", { mode: 0o600 })
    created += 1
  }
  return created
}

async function runCapture(ctx: any, sessionID: string, lastHashes: Map<string, string>, active: Set<string>) {
  if (active.has(sessionID)) return
  active.add(sessionID)
  try {
    if (typeof ctx.session?.context !== "function") return
    const messages = await ctx.session.context({ sessionID })
    if (!Array.isArray(messages)) return
    const maxInput = intEnv("OAT_MEMORY_CAPTURE_MAX_INPUT_CHARS", 18000, 2000)
    const transcript = transcriptFromContext(messages, maxInput)
    if (!transcript || !/^USER:/m.test(transcript)) return
    const transcriptHash = createHash("sha256").update(transcript).digest("hex")
    if (lastHashes.get(sessionID) === transcriptHash) return
    lastHashes.set(sessionID, transcriptHash)

    const project = await projectInfo(ctx)
    const model = process.env.OAT_MEMORY_EXTRACTOR_MODEL || process.env.MODEL_LOW || ""
    const response = await generate(ctx, sessionID, buildPrompt(project.id, project.name, transcript), model)
    const payload = extractJson(response)
    const candidates = validateCandidates(payload, intEnv("OAT_MEMORY_MAX_CANDIDATES_PER_SESSION", 5, 1))
    if (!candidates.length) return
    await persist(stateRoot(), sessionID, project.id, project.name, model || "session-model", candidates)
  } catch (error) {
    if (truthy(process.env.OAT_MEMORY_CAPTURE_STRICT, false)) throw error
    console.warn("OpenCode memory capture:", error instanceof Error ? error.message : String(error))
  } finally {
    active.delete(sessionID)
  }
}

async function eventLoop(ctx: any, signal: AbortSignal) {
  const lastHashes = new Map<string, string>()
  const active = new Set<string>()
  while (!signal.aborted) {
    try {
      const stream = ctx.event.subscribe({ signal })
      for await (const event of stream as AsyncIterable<any>) {
        if (signal.aborted) break
        const idleEvent = event?.type === "session.idle"
        const idleStatus = event?.type === "session.status" && event?.properties?.status?.type === "idle"
        if (!idleEvent && !idleStatus) continue
        const sessionID = event?.properties?.sessionID
        if (typeof sessionID !== "string" || !sessionID) continue
        void runCapture(ctx, sessionID, lastHashes, active)
      }
      if (!signal.aborted) await new Promise((resolve) => setTimeout(resolve, 1000))
    } catch (error) {
      if (signal.aborted) break
      console.warn("OpenCode memory capture event stream:", error instanceof Error ? error.message : String(error))
      await new Promise((resolve) => setTimeout(resolve, 1500))
    }
  }
}

export default {
  id: "oat.memory-capture",
  async setup(ctx: any) {
    if (!truthy(process.env.OAT_MEMORY_ENABLED, false) || !truthy(process.env.OAT_MEMORY_CAPTURE_ENABLED, false)) return
    if (typeof ctx.event?.subscribe !== "function") {
      if (truthy(process.env.OAT_MEMORY_CAPTURE_STRICT, false)) throw new Error("OpenCode V2 ctx.event.subscribe is required for memory capture")
      console.warn("OpenCode memory capture: ctx.event.subscribe unavailable; capture disabled for this run")
      return
    }
    const controller = new AbortController()
    void eventLoop(ctx, controller.signal)
    return () => controller.abort()
  },
}
