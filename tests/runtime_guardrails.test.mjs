import assert from "node:assert/strict"
import test from "node:test"
import {
  createCallIdTracker,
  createProgressAwareRepeatDetector,
  providerRetryDecision,
} from "../.opencode/plugins/reliability-core.js"
import { ReliabilityV1Plugin } from "../.opencode/plugins/reliability-v1.js"

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const withEnv = async (values, fn) => {
  const previous = new Map()
  for (const [key, value] of Object.entries(values)) {
    previous.set(key, process.env[key])
    if (value === undefined) delete process.env[key]
    else process.env[key] = String(value)
  }
  try {
    return await fn()
  } finally {
    for (const [key, value] of previous.entries()) {
      if (value === undefined) delete process.env[key]
      else process.env[key] = value
    }
  }
}

const makeClient = () => {
  const aborts = []
  return {
    aborts,
    client: {
      session: {
        children: async () => ({ data: [] }),
        abort: async ({ path }) => {
          aborts.push(path.id)
        },
      },
      app: { log: async () => {} },
    },
  }
}

test("fallback call IDs are stable, FIFO, and unique for concurrent identical calls", () => {
  const tracker = createCallIdTracker()
  const call = { sessionID: "parent", tool: "task", args: { prompt: "same" } }
  const first = tracker.begin(call)
  const second = tracker.begin(call)

  assert.notEqual(first, second)
  assert.deepEqual(tracker.pending(call), [first, second])
  assert.equal(tracker.end(call), first)
  assert.equal(tracker.end(call), second)
  assert.deepEqual(tracker.pending(call), [])
})

test("repeat detection resets after material progress", () => {
  const detector = createProgressAwareRepeatDetector()
  const sample = { sessionID: "child", tool: "bash", args: "{\"cmd\":\"git status\"}", result: "clean" }

  assert.deepEqual(detector.observe(sample), { same: false, count: 1 })
  assert.deepEqual(detector.observe(sample), { same: true, count: 2 })

  detector.markProgress("child")
  assert.deepEqual(detector.observe(sample), { same: false, count: 1 })
  assert.deepEqual(detector.observe(sample), { same: true, count: 2 })
})

test("provider retry policy stops terminal errors and bounds transient retries", () => {
  assert.deepEqual(providerRetryDecision({ status: 401, attempt: 1, maxRetries: 2 }), { retry: false })
  assert.deepEqual(providerRetryDecision({ status: 404, attempt: 1, maxRetries: 2 }), { retry: false })
  assert.deepEqual(providerRetryDecision({ status: 429, attempt: 1, maxRetries: 2 }), { retry: true, delay: 1000 })
  assert.deepEqual(providerRetryDecision({ status: 503, attempt: 2, maxRetries: 2 }), { retry: true, delay: 2000 })
  assert.deepEqual(providerRetryDecision({ status: 503, attempt: 4, maxRetries: 2 }), { retry: false })
})

test("V1 fallback task reservation is released after execute.after", async () => {
  await withEnv(
    {
      MAX_PARALLEL_SUBAGENTS: 1,
      SUBAGENT_QUEUE_TIMEOUT_SECONDS: 1,
      SUBAGENT_STALLED_TIMEOUT_SECONDS: 30,
      SUBAGENT_MAX_DURATION_SECONDS: 60,
      SUBAGENT_WATCH_INTERVAL_SECONDS: 1,
      MAX_CHILD_COST: 0,
      MAX_RUN_COST: 0,
    },
    async () => {
      const { client } = makeClient()
      const hooks = await ReliabilityV1Plugin({ client })
      const input = { sessionID: "parent", tool: "task", args: { prompt: "same" } }

      await hooks["tool.execute.before"](input, { args: input.args })
      await hooks["tool.execute.after"](input, { output: "done" })

      const started = Date.now()
      await hooks["tool.execute.before"](input, { args: input.args })
      assert.ok(Date.now() - started < 250, "released fallback reservation should not block the next task")
      await hooks["tool.execute.after"](input, { output: "done again" })
    },
  )
})

test("V1 cost guard applies message cost to the child session, not the message ID", async () => {
  await withEnv(
    {
      MAX_CHILD_COST: 0.1,
      MAX_RUN_COST: 0,
      SUBAGENT_STALLED_TIMEOUT_SECONDS: 30,
      SUBAGENT_MAX_DURATION_SECONDS: 60,
      SUBAGENT_WATCH_INTERVAL_SECONDS: 1,
    },
    async () => {
      const { client, aborts } = makeClient()
      const hooks = await ReliabilityV1Plugin({ client })

      await hooks.event({
        event: { type: "session.created", properties: { info: { id: "child", parentID: "parent" } } },
      })
      await hooks.event({
        event: {
          type: "message.updated",
          properties: {
            info: { id: "message-1", sessionID: "child", role: "assistant", cost: 0.2 },
          },
        },
      })

      assert.deepEqual(aborts, ["child"])
    },
  )
})

test("WAITING_PERMISSION is exempt from stall timeout, then stall protection resumes", async () => {
  await withEnv(
    {
      MAX_CHILD_COST: 0,
      MAX_RUN_COST: 0,
      SUBAGENT_STALLED_TIMEOUT_SECONDS: 1,
      SUBAGENT_MAX_DURATION_SECONDS: 30,
      SUBAGENT_WATCH_INTERVAL_SECONDS: 1,
    },
    async () => {
      const { client, aborts } = makeClient()
      const hooks = await ReliabilityV1Plugin({ client })

      await hooks.event({
        event: { type: "session.created", properties: { info: { id: "child", parentID: "parent" } } },
      })
      await hooks.event({ event: { type: "permission.asked", properties: { sessionID: "child" } } })
      await sleep(1200)
      assert.deepEqual(aborts, [], "permission wait must not be treated as a stall")

      await hooks.event({ event: { type: "permission.replied", properties: { sessionID: "child" } } })
      await sleep(2200)
      assert.deepEqual(aborts, ["child"], "stall protection must resume after permission is answered")
    },
  )
})
