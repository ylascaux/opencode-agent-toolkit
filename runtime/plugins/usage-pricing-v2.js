const finite = (value) =>
  typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : 0

const unwrap = (value) =>
  value && typeof value === "object" && "data" in value ? value.data : value

export function tokenTotal(tokens = {}) {
  return (
    finite(tokens.input) +
    finite(tokens.output) +
    finite(tokens.reasoning) +
    finite(tokens.cache?.read) +
    finite(tokens.cache?.write)
  )
}

export function estimateCost(tokens = {}, pricing) {
  if (!pricing || typeof pricing !== "object") return undefined
  const input = finite(pricing.input)
  const output = finite(pricing.output)
  const cacheRead = finite(pricing.cache?.read)
  const cacheWrite = finite(pricing.cache?.write)
  if (input === 0 && output === 0 && cacheRead === 0 && cacheWrite === 0) return undefined

  return (
    finite(tokens.input) * input +
    (finite(tokens.output) + finite(tokens.reasoning)) * output +
    finite(tokens.cache?.read) * cacheRead +
    finite(tokens.cache?.write) * cacheWrite
  ) / 1_000_000
}

function providerList(value) {
  const body = unwrap(value)
  if (Array.isArray(body)) return body
  if (Array.isArray(body?.providers)) return body.providers
  if (body?.providers && typeof body.providers === "object") return Object.values(body.providers)
  if (body && typeof body === "object") return Object.values(body)
  return []
}

export function findModel(value, providerID, modelID) {
  if (!providerID || !modelID) return undefined
  const provider = providerList(value).find((candidate) => candidate?.id === providerID)
  if (!provider) return undefined
  const models = provider.models
  if (Array.isArray(models)) return models.find((model) => model?.id === modelID)
  if (!models || typeof models !== "object") return undefined
  return models[modelID] ?? Object.values(models).find((model) => model?.id === modelID)
}

function modelRef(session = {}) {
  const model = session.model ?? {}
  return {
    providerID: model.providerID ?? session.providerID,
    modelID: model.id ?? model.modelID ?? session.modelID,
  }
}

function fingerprint(session) {
  const ref = modelRef(session)
  const tokens = session.tokens ?? {}
  return JSON.stringify([
    ref.providerID,
    ref.modelID,
    finite(tokens.input),
    finite(tokens.output),
    finite(tokens.reasoning),
    finite(tokens.cache?.read),
    finite(tokens.cache?.write),
    finite(session.cost),
  ])
}

function formatCost(cost, estimated) {
  if (!(cost > 0)) return "cost unavailable"
  const formatted = cost < 0.01 ? cost.toFixed(4) : cost.toFixed(2)
  return `${estimated ? "~" : ""}$${formatted}`
}

export const UsagePricingV2 = async ({ client }) => {
  const seen = new Map()
  let providers

  async function pricing() {
    if (providers !== undefined) return providers
    const response = await client.config.providers()
    providers = response
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

export default UsagePricingV2
