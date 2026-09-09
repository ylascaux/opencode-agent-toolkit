import { Plugin } from "@opencode/plugin/tui"
import { ReliabilityApproval } from "./rpc.js"

export default Plugin.define({
  id: "agent-reliability-approval-tui",
  async setup(context) {
    const rpc = context.client.rpc(ReliabilityApproval)
    let queue = Promise.resolve()

    const handle = async (event: any) => {
      const data = event?.data ?? {}
      const reason =
        data.reason === "max-duration"
          ? `running for ${data.ageSeconds}s`
          : `no observable activity for ${data.noActivitySeconds}s and no material progress for ${data.noProgressSeconds}s`

      const confirmed = await context.ui.dialog.confirm({
        title: "Possible stalled subagent",
        message: [
          `${data.agent} (${data.sessionID}) looks suspicious: ${reason}.`,
          "OpenCode telemetry can be incomplete, so this is not proof that the agent is stuck.",
          "Kill this subagent?",
        ].join("\n\n"),
        label: { confirm: "Kill", cancel: "Keep running" },
      })

      const result = await rpc.decide({
        sessionID: String(data.sessionID),
        action: confirmed ? "kill" : "keep",
      })

      if (result.status === "killed") {
        context.ui.toast.show({
          title: "Reliability watchdog",
          message: `Killed ${data.agent} (${data.sessionID}) by user approval.`,
          variant: "warning",
        })
      } else if (result.status === "kept") {
        context.ui.toast.show({
          title: "Reliability watchdog",
          message: `Keeping ${data.agent} running.`,
          variant: "success",
        })
      } else if (result.status === "stale") {
        context.ui.toast.show({
          title: "Reliability watchdog",
          message: `${data.agent} became active again; no action was taken.`,
          variant: "info",
        })
      }
    }

    const unsubscribe = rpc.events.on("suspected", (event: any) => {
      queue = queue.then(() => handle(event)).catch((error) => {
        context.ui.toast.show({
          title: "Reliability watchdog",
          message: `Approval dialog failed safely: ${String(error)}`,
          variant: "error",
        })
      })
    })

    return () => unsubscribe()
  },
})
