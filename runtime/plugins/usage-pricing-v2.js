import {
  estimateCost,
  findModel,
  fingerprint,
  finite,
  formatCost,
  modelRef,
  tokenTotal,
  unwrap,
} from "./usage-pricing-core.js"

export const UsagePricingV2 = async ({ client }) => {
  const seen = new Map()
  let providers

  async function pricing() {
    if (providers !== undefined) return providers
    providers = await client.config.providers()
    return providers
  }

  return {
    event: async ({ event }) => {
      if (event?.type !== "session.idle") return
      const sessionID = event.properties?.sessionID
      if (!sessionID) return

      try {
        const response = await client.session.get({ path: { id: sessionID } })
        const session = unwrap(response)
        if (!session || typeof session !== "object") return

        const total = tokenTotal(session.tokens)
        if (total <= 0) return
        const current = fingerprint(session)
        if (seen.get(sessionID) === current) return
        seen.set(sessionID, current)

        let cost = finite(session.cost)
        let estimated = false
        const ref = modelRef(session)
        if (!(cost > 0)) {
          const model = findModel(await pricing(), ref.providerID, ref.modelID)
          const estimate = estimateCost(session.tokens, model?.cost)
          if (estimate !== undefined && estimate > 0) {
            cost = estimate
            estimated = true
          }
        }

        const modelName = [ref.providerID, ref.modelID].filter(Boolean).join("/") || "unknown model"
        const kind = session.parentID ? "subagent" : "root"
        const count = new Intl.NumberFormat("en-US").format(total)
        await client.tui.showToast({
          body: {
            title: `OC2 usage · ${kind}`,
            message: `${count} tokens · ${formatCost(cost, estimated)} · ${modelName}`,
            variant: "info",
            duration: 6000,
          },
        })
      } catch {
        // Observability must never block or fail an OpenCode session.
      }
    },
  }
}
