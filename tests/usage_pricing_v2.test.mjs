import assert from "node:assert/strict"
import test from "node:test"

import UsagePricingV2, { estimateCost, findModel, tokenTotal } from "../runtime/plugins/usage-pricing-v2.js"

const tokens = {
  input: 1_000_000,
  output: 100_000,
  reasoning: 50_000,
  cache: { read: 500_000, write: 20_000 },
}

const model = {
  id: "gpt-5.6-terra",
  cost: { input: 2, output: 10, cache: { read: 0.2, write: 2.5 } },
}

const providers = {
  data: {
    providers: [{ id: "github-copilot", models: { "gpt-5.6-terra": model } }],
  },
}

test("estimates all OC2 token classes without treating reasoning as free", () => {
  assert.equal(tokenTotal(tokens), 1_670_000)
  assert.equal(estimateCost(tokens, model.cost), 3.65)
})

test("returns unknown pricing instead of a false zero cost", () => {
  assert.equal(estimateCost(tokens, undefined), undefined)
  assert.equal(estimateCost(tokens, { input: 0, output: 0, cache: { read: 0, write: 0 } }), undefined)
})

test("finds model pricing in provider metadata", () => {
  assert.equal(findModel(providers, "github-copilot", "gpt-5.6-terra"), model)
  assert.equal(findModel(providers, "github-copilot", "missing"), undefined)
})

test("surfaces estimated pricing for an idle OC2 session and deduplicates repeats", async () => {
  const toasts = []
  const plugin = await UsagePricingV2({
    client: {
      session: {
        get: async () => ({
          data: {
            id: "ses_root",
            cost: 0,
            tokens,
            model: { providerID: "github-copilot", id: "gpt-5.6-terra" },
          },
        }),
      },
      config: { providers: async () => providers },
      tui: { showToast: async (payload) => toasts.push(payload.body) },
    },
  })

  const idle = { event: { type: "session.idle", properties: { sessionID: "ses_root" } } }
  await plugin.event(idle)
  await plugin.event(idle)

  assert.equal(toasts.length, 1)
  assert.equal(toasts[0].title, "OC2 usage · root")
  assert.match(toasts[0].message, /1,670,000 tokens/)
  assert.match(toasts[0].message, /~\$3\.65/)
  assert.match(toasts[0].message, /github-copilot\/gpt-5\.6-terra/)
})

test("marks unavailable pricing explicitly for subagents", async () => {
  const toasts = []
  const plugin = await UsagePricingV2({
    client: {
      session: {
        get: async () => ({
          data: {
            id: "ses_child",
            parentID: "ses_root",
            cost: 0,
            tokens: { input: 1_000, output: 200, reasoning: 0, cache: { read: 0, write: 0 } },
            model: { providerID: "unknown", id: "custom" },
          },
        }),
      },
      config: { providers: async () => ({ data: { providers: [] } }) },
      tui: { showToast: async (payload) => toasts.push(payload.body) },
    },
  })

  await plugin.event({ event: { type: "session.idle", properties: { sessionID: "ses_child" } } })

  assert.equal(toasts.length, 1)
  assert.equal(toasts[0].title, "OC2 usage · subagent")
  assert.match(toasts[0].message, /cost unavailable/)
  assert.doesNotMatch(toasts[0].message, /\$0(?:\.0+)?/)
})

test("observability failures never fail the OC2 session", async () => {
  const plugin = await UsagePricingV2({
    client: {
      session: { get: async () => { throw new Error("server unavailable") } },
      config: { providers: async () => { throw new Error("provider unavailable") } },
      tui: { showToast: async () => { throw new Error("no tui") } },
    },
  })

  await assert.doesNotReject(() =>
    plugin.event({ event: { type: "session.idle", properties: { sessionID: "ses_failure" } } }),
  )
})
