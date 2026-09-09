import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { Plugin } from "@opencode/plugin"
import { createPlanApprovalGate } from "./plan-approval-core.js"

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..")
const POLICY = JSON.parse(fs.readFileSync(path.join(ROOT, "reliability.json"), "utf8"))

const eventProps = (event: any) => event?.properties ?? event?.data ?? event ?? {}
const sessionInfo = (event: any) => {
  const p = eventProps(event)
  const info = p.info ?? p.session ?? p
  return {
    id: info?.sessionID ?? p.sessionID ?? p.sessionId ?? event?.sessionID ?? info?.id,
    parentID: info?.parentID ?? info?.parentId ?? info?.parent?.id ?? p.parentID ?? p.parentId,
  }
}

const effectiveMode = () =>
  String(process.env.PLAN_APPROVAL_MODE || POLICY.plan_approval?.default_mode || "changes")

const blockedMessage = (decision: any) => [
  `Plan approval gate blocked this change (mode=${decision.mode}).`,
  "Stop execution and present a concise implementation plan before retrying any mutating tool.",
  "The plan must include goal/scope, affected files or components, ordered steps, validation/tests, rollback, and delegated agents/gates when relevant.",
  "End the response with the literal marker PLAN_APPROVAL_REQUIRED and wait for an explicit user approval such as: go, approve, oui, or valide.",
  "If the approved scope must materially change later, stop and end the revised plan with PLAN_REAPPROVAL_REQUIRED before further mutation.",
].join(" ")

export default Plugin.define({
  id: "plan-approval-gate-v2",
  async setup(ctx) {
    const gate = createPlanApprovalGate({ mode: effectiveMode() })
    const messageRoles = new Map<string, string>()
    const pendingText = new Map<string, { sessionID: string; text: string }>()

    const processMessageText = (messageID: string, sessionID: string, text: string) => {
      const role = messageRoles.get(messageID)
      if (!role) {
        pendingText.set(messageID, { sessionID, text })
        return
      }
      if (role === "user") gate.onUserMessage(sessionID, text, messageID)
      if (role === "assistant") gate.onAssistantText(sessionID, text, messageID)
    }

    const controller = new AbortController()
    void (async () => {
      for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
        const type = event?.type
        const p: any = eventProps(event)
        const { id, parentID } = sessionInfo(event)
        if (id && parentID) gate.rememberParent(String(id), String(parentID))

        if (type === "message.updated") {
          const info = p.info ?? p.message ?? p
          const messageID = String(info?.id ?? info?.messageID ?? "")
          const sessionID = String(info?.sessionID ?? p.sessionID ?? id ?? "")
          const role = String(info?.role ?? "")
          if (messageID && role) {
            messageRoles.set(messageID, role)
            const pending = pendingText.get(messageID)
            if (pending) {
              processMessageText(messageID, pending.sessionID || sessionID, pending.text)
              pendingText.delete(messageID)
            }
          }
        }

        if (type === "message.part.updated") {
          const part = p.part
          if (part?.type !== "text" || typeof part?.text !== "string") continue
          const messageID = String(part.messageID ?? p.messageID ?? "")
          const sessionID = String(part.sessionID ?? p.sessionID ?? id ?? "")
          if (messageID && sessionID) processMessageText(messageID, sessionID, part.text)
        }
      }
    })().catch((error) => {
      if (!controller.signal.aborted) {
        console.warn(`[plan-approval] event tracking failed closed for future mutations: ${String(error)}`)
      }
    })

    const registration = await ctx.tool.hook("execute.before", async (event: any) => {
      const sessionID = String(event?.sessionID ?? event?.sessionId ?? event?.context?.sessionID ?? "")
      if (!sessionID) return
      const tool = String(event?.tool ?? event?.name ?? "")
      const args = event?.args ?? event?.input ?? {}
      const decision = gate.beforeTool(sessionID, tool, args)
      if (!decision.allowed) throw new Error(blockedMessage(decision))
    })

    return async () => {
      controller.abort()
      const dispose = (registration as any)?.dispose
      if (typeof dispose === "function") await dispose.call(registration)
    }
  },
})
