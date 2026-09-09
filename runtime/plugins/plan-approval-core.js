export const PLAN_REQUIRED_MARKER = "PLAN_APPROVAL_REQUIRED"
export const PLAN_REAPPROVAL_MARKER = "PLAN_REAPPROVAL_REQUIRED"

export const PLAN_APPROVAL_MODES = new Set(["off", "changes", "always"])

const APPROVAL_RE = /^(approve|approved|approve plan|approve the plan|go|yes|oui|ok|okay|valide|validé|valider|valide le plan|execute|exécute|execute plan|exécute le plan)$/i
const REJECTION_RE = /^(reject|rejected|no|non|stop|cancel|annule|annuler|rejette|rejeté)$/i

const READ_ONLY_SIMPLE = [
  /^pwd(?:\s|$)/,
  /^ls(?:\s|$)/,
  /^tree(?:\s|$)/,
  /^file(?:\s|$)/,
  /^which(?:\s|$)/,
  /^head(?:\s|$)/,
  /^tail(?:\s|$)/,
  /^wc(?:\s|$)/,
  /^sort(?:\s|$)/,
  /^uniq(?:\s|$)/,
  /^cut(?:\s|$)/,
  /^jq(?:\s|$)/,
  /^yq(?:\s|$)/,
  /^rg(?:\s|$)/,
  /^grep(?:\s|$)/,
  /^cat(?:\s|$)/,
  /^sed\s+-n(?:\s|$)/,
  /^awk(?:\s|$)/,
  /^test(?:\s|$)/,
  /^\[(?:\s|$)/,
  /^fd(?:\s|$)/,
  /^echo(?:\s|$)/,
  /^printf(?:\s|$)/,
  /^hostname(?:\s|$)/,
  /^printenv(?:\s|$)/,
  /^env(?:\s|$)/,
  /^id(?:\s|$)/,
  /^uname(?:\s|$)/,
  /^whoami(?:\s|$)/,
  /^true(?:\s|$)/,
  /^find(?:\s|$)/,
  /^git\s+(?:--no-pager\s+)?(?:status|diff|show|log|rev-parse|rev-list|ls-files|ls-tree|grep|blame|describe|merge-base)(?:\s|$)/,
  /^git\s+(?:--no-pager\s+)?remote\s+(?:-v|get-url)(?:\s|$)/,
  /^git\s+(?:--no-pager\s+)?branch\s+--show-current(?:\s|$)/,
  /^git\s+(?:--no-pager\s+)?tag\s+--list(?:\s|$)/,
  /^git\s+(?:--no-pager\s+)?config\s+(?:--get|--list)(?:\s|$)/,
  /^(?:pytest|python3?\s+-m\s+pytest)(?:\s|$)/,
  /^go\s+test(?:\s|$)/,
  /^cargo\s+test(?:\s|$)/,
  /^(?:npm|pnpm|yarn)\s+(?:run\s+)?test(?:\s|$)/,
  /^(?:just|make)\s+test(?:\s|$)/,
  /^(?:terraform|tofu)\s+(?:validate|plan|show|providers|version)(?:\s|$)/,
  /^terragrunt\s+(?:validate|plan|show)(?:\s|$)/,
  /^helm\s+(?:template|lint|show)(?:\s|$)/,
  /^kubectl\s+(?:get|describe|logs|explain|version|api-resources|api-versions)(?:\s|$)/,
  /^docker\s+(?:ps|images|logs|inspect|version)(?:\s|$)/,
]

const PLAN_SAFE_DELEGATIONS = new Set([
  "meta-router",
  "orchestrator",
  "planner",
  "project-scanner",
  "brainstorm",
  "deep-reasoner",
  "arbiter",
  "evidence-auditor",
  "review-lead",
  "reviewer",
  "platform-architect",
  "security-lead",
  "threat-model",
  "appsec",
  "iac-security",
  "secrets",
  "supply-chain",
])

export function normalizePlanApprovalMode(value, fallback = "changes") {
  const candidate = String(value ?? fallback).trim().toLowerCase()
  return PLAN_APPROVAL_MODES.has(candidate) ? candidate : fallback
}

export function isApprovalMessage(text) {
  return APPROVAL_RE.test(String(text ?? "").trim())
}

export function isRejectionMessage(text) {
  return REJECTION_RE.test(String(text ?? "").trim())
}

export function containsPlanApprovalMarker(text) {
  return String(text ?? "").includes(PLAN_REQUIRED_MARKER)
}

export function containsPlanReapprovalMarker(text) {
  return String(text ?? "").includes(PLAN_REAPPROVAL_MARKER)
}

function shellWords(command) {
  const words = []
  let current = ""
  let quote = null
  let escaped = false
  let started = false

  for (const char of String(command ?? "")) {
    if (escaped) {
      current += char
      escaped = false
      started = true
      continue
    }
    if (quote === "'") {
      if (char === "'") quote = null
      else current += char
      started = true
      continue
    }
    if (quote === '"') {
      if (char === '"') quote = null
      else if (char === "\\") escaped = true
      else current += char
      started = true
      continue
    }
    if (char === "'" || char === '"') {
      quote = char
      started = true
      continue
    }
    if (char === "\\") {
      escaped = true
      started = true
      continue
    }
    if (/\s/.test(char)) {
      if (started) {
        words.push(current)
        current = ""
        started = false
      }
      continue
    }
    current += char
    started = true
  }

  if (quote || escaped) return null
  if (started) words.push(current)
  return words
}

function unwrapSandboxCommand(command) {
  const words = shellWords(command)
  if (!words) return { matched: false, command: null }
  if (words.length !== 6) return { matched: false, command: null }
  if (words[0] !== "bash") return { matched: false, command: null }
  if (!/(?:^|\/)scripts\/sandbox-run$/.test(words[1])) return { matched: false, command: null }
  if (words[2] !== "--cwd" || words[4] !== "--command") return { matched: false, command: null }
  return { matched: true, command: words[5] }
}

function isReadOnlySimpleCommand(command) {
  const value = command.trim()
  if (!value) return true
  if (/\bfind\b[\s\S]*\s-delete(?:\s|$)/.test(value)) return false
  return READ_ONLY_SIMPLE.some((pattern) => pattern.test(value))
}

export function isReadOnlyShellCommand(command) {
  const raw = String(command ?? "").trim()
  if (!raw) return true

  const sandbox = unwrapSandboxCommand(raw)
  const value = sandbox.matched ? String(sandbox.command ?? "").trim() : raw
  if (!value) return true

  // Redirections, command substitution and multi-command control operators can
  // hide writes even when the visible prefix looks read-only. The sandbox
  // wrapper itself is trusted and removed before applying this classification.
  if (/[<>`\n]/.test(value) || /\$\(/.test(value) || /(?:&&|\|\||;)/.test(value)) return false

  // Read-only pipelines are allowed only when every stage is independently
  // classified as read-only.
  return value.split("|").every((part) => isReadOnlySimpleCommand(part))
}

function delegatedAgent(args = {}) {
  return String(
    args.subagent_type ?? args.subagentType ?? args.agent ?? args.agent_name ?? args.agentName ?? "",
  ).trim()
}

export function toolRequiresPlanApproval(tool, args = {}, mode = "changes") {
  const normalizedMode = normalizePlanApprovalMode(mode)
  if (normalizedMode === "off") return false

  const name = String(tool ?? "").trim().toLowerCase()
  if (!name) return false

  if (["edit", "write", "patch", "apply_patch", "apply-patch"].includes(name)) return true
  if (/(?:^|[._-])(edit|write|patch|delete|remove|move|rename|create)(?:$|[._-])/.test(name)) return true

  if (name === "bash" || name === "shell") {
    return !isReadOnlyShellCommand(args.command ?? args.cmd ?? args.script ?? "")
  }

  if (name === "task" || name === "subagent") {
    if (normalizedMode === "always") return true
    const agent = delegatedAgent(args)
    return agent ? !PLAN_SAFE_DELEGATIONS.has(agent) : true
  }

  if (normalizedMode === "always") {
    // Discovery/research tools remain available so a plan can be created.
    return ![
      "read", "glob", "grep", "webfetch", "websearch", "question", "todo", "todoread", "todowrite",
    ].includes(name)
  }

  return false
}

const STATUS_PRIORITY = {
  idle: 0,
  planning: 1,
  approved: 2,
  rejected: 3,
  waiting: 4,
}

function mergeStatus(a, b) {
  return STATUS_PRIORITY[b] > STATUS_PRIORITY[a] ? b : a
}

export function createPlanApprovalGate({ mode = "changes", onStateChange } = {}) {
  const effectiveMode = normalizePlanApprovalMode(mode)
  const parents = new Map()
  const states = new Map()
  const processedUser = new Map()
  const processedAssistant = new Map()

  const rootOf = (sessionID) => {
    let current = sessionID
    const seen = new Set()
    while (current && !seen.has(current)) {
      seen.add(current)
      const parent = parents.get(current)
      if (!parent) return current
      current = parent
    }
    return sessionID
  }

  const stateFor = (sessionID) => {
    const root = rootOf(sessionID)
    if (!states.has(root)) states.set(root, { status: "planning", reason: "new-session" })
    return [root, states.get(root)]
  }

  const setState = (sessionID, status, reason) => {
    const [root, previous] = stateFor(sessionID)
    const next = { status, reason }
    states.set(root, next)
    onStateChange?.({ rootSessionID: root, previous, next })
    return next
  }

  const rememberParent = (sessionID, parentID) => {
    if (!sessionID || !parentID || sessionID === parentID) return
    const oldRoot = rootOf(sessionID)
    parents.set(sessionID, parentID)
    const newRoot = rootOf(sessionID)
    if (oldRoot !== newRoot && states.has(oldRoot)) {
      const childState = states.get(oldRoot)
      const rootState = states.get(newRoot) ?? { status: "planning", reason: "new-session" }
      const status = mergeStatus(rootState.status, childState.status)
      states.set(newRoot, status === childState.status ? childState : rootState)
      states.delete(oldRoot)
    }
  }

  const onUserMessage = (sessionID, text, messageID = "") => {
    if (!sessionID || effectiveMode === "off") return
    const root = rootOf(sessionID)
    // Subagent prompts are implementation details, not new user turns.
    if (root !== sessionID) return

    const normalized = String(text ?? "").trim()
    const dedupKey = messageID || `${sessionID}:${normalized}`
    if (processedUser.get(dedupKey) === normalized) return
    processedUser.set(dedupKey, normalized)

    const [, current] = stateFor(root)
    if (current.status === "waiting" && isApprovalMessage(normalized)) {
      setState(root, "approved", "user-approved")
      return
    }
    if (current.status === "waiting" && isRejectionMessage(normalized)) {
      setState(root, "rejected", "user-rejected")
      return
    }

    // Any other root user turn creates or changes scope. Previous approval is
    // intentionally one-shot for that request and must not leak into the next.
    setState(root, "planning", current.status === "waiting" ? "plan-change-requested" : "new-user-turn")
  }

  const onAssistantText = (sessionID, text, messageID = "") => {
    if (!sessionID || effectiveMode === "off") return
    const value = String(text ?? "")
    const dedupKey = messageID || `${sessionID}:${value}`
    if (processedAssistant.get(dedupKey) === value) return
    processedAssistant.set(dedupKey, value)

    if (containsPlanReapprovalMarker(value)) {
      setState(sessionID, "waiting", "scope-deviation")
      return
    }
    if (containsPlanApprovalMarker(value)) setState(sessionID, "waiting", "plan-presented")
  }

  const beforeTool = (sessionID, tool, args = {}) => {
    if (!sessionID || effectiveMode === "off") return { allowed: true, mode: effectiveMode }
    if (!toolRequiresPlanApproval(tool, args, effectiveMode)) return { allowed: true, mode: effectiveMode }

    const [root, state] = stateFor(sessionID)
    if (state.status === "approved") return { allowed: true, mode: effectiveMode, rootSessionID: root }

    if (state.status !== "waiting") setState(root, "waiting", "runtime-blocked-unapproved-change")
    const blockedState = states.get(root)
    return {
      allowed: false,
      mode: effectiveMode,
      rootSessionID: root,
      status: blockedState.status,
      reason: blockedState.reason,
    }
  }

  return {
    mode: effectiveMode,
    rememberParent,
    rootOf,
    onUserMessage,
    onAssistantText,
    beforeTool,
    state(sessionID) {
      const [root, state] = stateFor(sessionID)
      return { rootSessionID: root, ...state }
    },
  }
}
