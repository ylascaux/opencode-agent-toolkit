import { createHash } from "node:crypto"

export const ALLOWED_KINDS = new Set(["project_fact", "decision", "convention", "known_issue", "workstyle", "hat_preference"])
export const ALLOWED_CONFIDENCE = new Set(["medium", "high"])
export const SECRET_PATTERNS = [
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/i,
  /\bAKIA[0-9A-Z]{16}\b/,
  /\bgh[pousr]_[A-Za-z0-9_]{20,}\b/,
  /\bsk-[A-Za-z0-9_-]{20,}\b/,
  /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/,
  /\b(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*[^\s]{8,}/i,
]

export function textFromMessage(message) {
  if (!message || typeof message !== "object") return null
  if (message.type === "user" && typeof message.text === "string" && message.text.trim()) {
    return { role: "user", text: message.text.trim() }
  }
  if (message.type === "assistant" && Array.isArray(message.content)) {
    const text = message.content
      .filter((part) => part && part.type === "text" && typeof part.text === "string")
      .map((part) => part.text.trim())
      .filter(Boolean)
      .join("\n")
    return text ? { role: "assistant", text } : null
  }
  return null
}

export function transcriptFromContext(messages, maxChars) {
  const blocks = messages.flatMap((message) => {
    const parsed = textFromMessage(message)
    return parsed ? [`${parsed.role.toUpperCase()}:\n${parsed.text}`] : []
  })
  let transcript = blocks.join("\n\n").trim()
  if (transcript.length > maxChars) transcript = transcript.slice(transcript.length - maxChars)
  return transcript
}

export function extractJson(text) {
  const trimmed = String(text ?? "").trim()
  const unfenced = trimmed.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "")
  const start = unfenced.indexOf("{")
  const end = unfenced.lastIndexOf("}")
  if (start < 0 || end <= start) throw new Error("extractor did not return a JSON object")
  return JSON.parse(unfenced.slice(start, end + 1))
}

export function clean(value, max) {
  if (typeof value !== "string") return ""
  return value.replace(/\s+/g, " ").trim().slice(0, max)
}

export function containsSecret(value) {
  return SECRET_PATTERNS.some((pattern) => pattern.test(value))
}

export function validateCandidates(payload, maxCandidates = 5) {
  if (!payload || typeof payload !== "object") return []
  const raw = payload.candidates
  if (!Array.isArray(raw)) return []
  const output = []
  for (const item of raw) {
    if (!item || typeof item !== "object") continue
    const kind = clean(item.kind, 40)
    const title = clean(item.title, 120)
    const statement = clean(item.statement, 1200)
    const rationale = clean(item.rationale, 800)
    const confidence = clean(item.confidence, 20).toLowerCase()
    const suggested_target = clean(item.suggested_target, 160)
    const hats = Array.isArray(item.hats)
      ? item.hats.map((value) => clean(value, 80)).filter((value) => /^[a-z0-9][a-z0-9-]*$/.test(value)).slice(0, 4)
      : []
    if (!ALLOWED_KINDS.has(kind) || !ALLOWED_CONFIDENCE.has(confidence) || !title || !statement) continue
    const secretSurface = [title, statement, rationale, suggested_target, ...hats].join("\n")
    if (containsSecret(secretSurface)) continue
    output.push({
      kind,
      title,
      statement,
      rationale: rationale || undefined,
      confidence,
      suggested_target: suggested_target || undefined,
      hats: hats.length ? hats : undefined,
    })
    if (output.length >= maxCandidates) break
  }
  return output
}

export function fingerprint(projectID, candidate) {
  const stable = [projectID, candidate.kind, candidate.title.toLowerCase(), candidate.statement.toLowerCase()].join("\n")
  return createHash("sha256").update(stable).digest("hex")
}

export function buildPrompt(projectID, projectName, transcript) {
  return `You are a conservative long-term memory extractor for a software-engineering assistant.\n\nReturn ONLY JSON with this exact top-level shape:\n{"candidates":[{"kind":"project_fact|decision|convention|known_issue|workstyle|hat_preference","title":"short title","statement":"durable fact or preference","rationale":"optional short reason","confidence":"medium|high","suggested_target":"optional target","hats":["optional-hat"]}]}\n\nRules:\n- Extract only durable information that is likely useful in future sessions.\n- Do not store task-local chatter, transient logs, commands, raw error dumps, guesses, unresolved hypotheses, or assistant-generated assumptions.\n- Never include credentials, secrets, tokens, personal/private non-project information, or raw transcript excerpts.\n- A project fact must be about the current project.\n- Workstyle is only a stable preference explicitly expressed by the user.\n- Hat preferences describe how a reusable role should work, not project facts.\n- If evidence is weak or ambiguous, omit it. Prefer zero candidates over a bad candidate.\n- Maximum 5 candidates.\n\nCurrent project id: ${projectID || "unknown"}\nCurrent project name: ${projectName || "unknown"}\n\nConversation:\n${transcript}`
}
