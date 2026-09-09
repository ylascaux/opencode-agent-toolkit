import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { createPlanApprovalGate } from "./plan-approval-core.js"

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..")
const POLICY = JSON.parse(fs.readFileSync(path.join(ROOT, "reliability.json"), "utf8"))

const eventProps = (event) => event?.properties ?? event?.data ?? {}
const sessionInfo = (event) => {
  const p = eventProps(event)
  const info = p.info ?? p.session ?? p
  return {
    id: info?.sessionID ?? p.sessionID ?? p.sessionId ?? event?.sessionID ?? info?.id,
    parentID: info?.parentID ?? info?.parentId ?? info?.parent?.id ?? p.parentID ?? p.parentId,
  }
}
const hookSessionID = (input) =>
  input?.sessionID ?? input?.sessionId ?? input?.context?.sessionID ?? input?.context?.sessionId

const effectiveMode = () =>
  String(process.env.PLAN_APPROVAL_MODE || POLICY.plan_approval?.default_mode || "changes")

const textFromParts = (parts = []) =>
  parts
    .filter((part) => part?.type === "text" && typeof part?.text === "string")
    .map((part) => part.text)
    .join("\n")

const blockedMessage = (decision) => [
  `Plan approval gate blocked this change (mode=${decision.mode}).`,
  "Stop execution and present a concise implementation plan before retrying any mutating tool.",
  "The plan must include goal/scope, affected files or components, ordered steps, validation/tests, rollback, and delegated agents/gates when relevant.",
  "End the response with the literal marker PLAN_APPROVAL_REQUIRED and wait for an explicit user approval such as: go, approve, oui, or valide.",
  "If the approved scope must materially change later, stop and end the revised plan with PLAN_REAPPROVAL_REQUIRED before further mutation.",
].join(" ")

export const PlanApprovalV1Plugin = async () => {
  const gate = createPlanApprovalGate({ mode: effectiveMode() })
  const messageRoles = new Map()
  const pendingAssistantText = new Map()

  const processAssistantText = (messageID, sessionID, text) => {
    const role = messageRoles.get(messageID)
    if (!role) {
      pendingAssistantText.set(messageID, { sessionID, text })
      return
    }
    if (role === "assistant") gate.onAssistantText(sessionID, text, messageID)
  }

  return {
    // V1 exposes the complete user turn here. Keep this as the single source of
    // root-user approval/rejection so message events cannot process the same
    // short approval twice under a different deduplication key.
    "chat.message": async (input, output) => {
      const sessionID = hookSessionID(input)
      if (!sessionID) return
      const text = textFromParts(output?.parts)
      if (text) gate.onUserMessage(String(sessionID), text, String(input?.messageID ?? ""))
    },
    event: async ({ event }) => {
      const type = event?.type
      const p = eventProps(event)
      const { id, parentID } = sessionInfo(event)
      if (id && parentID) gate.rememberParent(String(id), String(parentID))

      if (type === "message.updated") {
        const info = p.info ?? p.message ?? p
        const messageID = String(info?.id ?? info?.messageID ?? "")
        const sessionID = String(info?.sessionID ?? p.sessionID ?? id ?? "")
        const role = String(info?.role ?? "")
        if (messageID && role) {
          messageRoles.set(messageID, role)
          const pending = pendingAssistantText.get(messageID)
          if (pending) {
            processAssistantText(messageID, pending.sessionID || sessionID, pending.text)
            pendingAssistantText.delete(messageID)
          }
        }
      }

      // Events are used only to observe assistant plan/reapproval markers.
      // User turns are deliberately ignored here; chat.message owns them.
      if (type === "message.part.updated") {
        const part = p.part
        if (part?.type !== "text" || typeof part?.text !== "string") return
        const messageID = String(part.messageID ?? p.messageID ?? "")
        const sessionID = String(part.sessionID ?? p.sessionID ?? id ?? "")
        if (messageID && sessionID) processAssistantText(messageID, sessionID, part.text)
      }
    },
    "tool.execute.before": async (input, output) => {
      const sessionID = hookSessionID(input)
      if (!sessionID) return
      const tool = String(input?.tool ?? input?.name ?? "")
      const args = output?.args ?? input?.args ?? {}
      const decision = gate.beforeTool(String(sessionID), tool, args)
      if (!decision.allowed) throw new Error(blockedMessage(decision))
    },
  }
}
