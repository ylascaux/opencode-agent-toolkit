export const finite = (value) =>
  typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : 0

export const unwrap = (value) =>
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

export function modelRef(session = {}) {
  const model = session.model ?? {}
  return {
    providerID: model.providerID ?? session.providerID,
    modelID: model.id ?? model.modelID ?? session.modelID,
  }
}

export function fingerprint(session) {
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

export function formatCost(cost, estimated) {
  if (!(cost > 0)) return "cost unavailable"
  const formatted = cost < 0.01 ? cost.toFixed(4) : cost.toFixed(2)
  return `${estimated ? "~" : ""}$${formatted}`
}
