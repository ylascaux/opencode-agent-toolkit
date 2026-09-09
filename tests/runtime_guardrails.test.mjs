import assert from "node:assert/strict"
import test from "node:test"
import {
  createCallIdTracker,
  createProgressAwareRepeatDetector,
  createStallDetector,
  delegationFailureClass,
  delegationTaskKey,
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

test("stall detection requires expired heartbeat and progress plus a confirmation cycle", () => {
  const detector = createStallDetector()
  const base = {
    sessionID: "child",
    heartbeatMs: 1000,
    stalledMs: 5000,
    confirmationMs: 1000,
    busy: false,
  }

  assert.deepEqual(
    detector.observe({ ...base, timestamp: 10_000, lastActivityAt: 9_500, lastProgressAt: 0 }),
    { stalled: false, suspect: false },
  )
  assert.deepEqual(
    detector.observe({ ...base, timestamp: 12_000, lastActivityAt: 10_000, lastProgressAt: 0 }),
    { stalled: false, suspect: true },
  )
  assert.deepEqual(
    detector.observe({ ...base, timestamp: 13_000, lastActivityAt: 10_000, lastProgressAt: 0 }),
    { stalled: true, suspect: false },
  )
})

test("stall suspicion resets when activity resumes or a tool is still in flight", () => {
  const detector = createStallDetector()
  const base = {
    sessionID: "child",
    heartbeatMs: 1000,
    stalledMs: 5000,
    confirmationMs: 1000,
  }

  assert.deepEqual(
    detector.observe({ ...base, timestamp: 10_000, lastActivityAt: 0, lastProgressAt: 0, busy: false }),
    { stalled: false, suspect: true },
  )
  assert.deepEqual(
    detector.observe({ ...base, timestamp: 10_500, lastActivityAt: 10_400, lastProgressAt: 0, busy: false }),
    { stalled: false, suspect: false },
  )
  assert.deepEqual(
    detector.observe({ ...base, timestamp: 20_000, lastActivityAt: 10_400, lastProgressAt: 0, busy: true }),
    { stalled: false, suspect: false },
  )
})

test("provider retry policy stops terminal errors and bounds transient retries", () => {
  assert.deepEqual(providerRetryDecision({ status: 401, attempt: 1, maxRetries: 2 }), { retry: false })
  assert.deepEqual(providerRetryDecision({ status: 404, attempt: 1, maxRetries: 2 }), { retry: false })
  assert.deepEqual(providerRetryDecision({ status: 429, attempt: 1, maxRetries: 2 }), { retry: true, delay: 1000 })
  assert.deepEqual(providerRetryDecision({ status: 503, attempt: 2, maxRetries: 2 }), { retry: true, delay: 2000 })
  assert.deepEqual(providerRetryDecision({ status: 503, attempt: 4, maxRetries: 2 }), { retry: false })
})

test("delegation failures distinguish retryable cancellation from terminal config errors", () => {
  assert.equal(delegationFailureClass("Task cancelled"), "retryable")
  assert.equal(delegationFailureClass("no-material-progress"), "retryable")
  assert.equal(delegationFailureClass("503 temporary upstream error"), "retryable")
  assert.equal(delegationFailureClass("403 forbidden"), "terminal")
  assert.equal(delegationFailureClass("unknown agent type"), "terminal")
  assert.equal(delegationFailureClass("application test failed"), "unknown")
})

test("delegation task keys are stable for the same parent, specialist and scope", () => {
  const first = delegationTaskKey({
    parentID: "platform",
    args: {
      subagent_type: "terraform-terragrunt",
      description: "Assess Terragrunt deployment semantics",
      prompt: "Inspect dependencies",
    },
  })
  const second = delegationTaskKey({
    parentID: "platform",
    args: {
      subagent_type: "terraform-terragrunt",
      description: "Assess Terragrunt deployment semantics",
      prompt: "Different continuation wording",
    },
  })
  assert.equal(first, second)
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
      await hooks.event({
        event: {
          type: "message.part.updated",
          properties: {
            sessionID: "parent",
            part: {
              type: "tool",
              tool: "task",
              state: {
                status: "completed",
                input: { prompt: "same" },
                metadata: { sessionId: "completed-child" },
                output: "done",
              },
            },
          },
        },
      })

      const started = Date.now()
      await hooks["tool.execute.before"](input, { args: input.args })
      assert.ok(Date.now() - started < 250, "released fallback reservation should not block the next task")
      await hooks["tool.execute.after"](input, { output: "done again" })
    },
  )
})

test("V1 cancelled leaf retry resumes the same task_id instead of creating a new child", async () => {
  await withEnv(
    {
      MAX_PARALLEL_SUBAGENTS: 2,
      MAX_SUBAGENT_RETRIES: 2,
      SUBAGENT_QUEUE_TIMEOUT_SECONDS: 2,
      SUBAGENT_STALLED_TIMEOUT_SECONDS: 30,
      SUBAGENT_MAX_DURATION_SECONDS: 60,
      SUBAGENT_WATCH_INTERVAL_SECONDS: 1,
      MAX_CHILD_COST: 0,
      MAX_RUN_COST: 0,
    },
    async () => {
      const { client } = makeClient()
      const hooks = await ReliabilityV1Plugin({ client })
      const args = {
        description: "Assess Terragrunt deployment semantics",
        prompt: "Inspect the existing Terragrunt deployment semantics and report evidence.",
        subagent_type: "terraform-terragrunt",
      }
      const firstInput = { sessionID: "platform-architect", tool: "task", args: { ...args } }
      const firstOutput = { args: { ...args } }

      await hooks["tool.execute.before"](firstInput, firstOutput)
      await hooks.event({
        event: {
          type: "session.created",
          properties: { info: { id: "leaf-task-1", parentID: "platform-architect" } },
        },
      })
      await hooks.event({
        event: {
          type: "message.part.updated",
          properties: {
            sessionID: "platform-architect",
            part: {
              type: "tool",
              tool: "task",
              state: {
                status: "error",
                input: { ...args },
                metadata: { sessionId: "leaf-task-1" },
                error: "Task cancelled",
              },
            },
          },
        },
      })

      const retryInput = { sessionID: "platform-architect", tool: "task", args: { ...args } }
      const retryOutput = { args: { ...args } }
      await hooks["tool.execute.before"](retryInput, retryOutput)

      assert.equal(retryOutput.args.task_id, "leaf-task-1")
      await hooks["tool.execute.after"](retryInput, { output: "retry scheduled" })
    },
  )
})

test("V1 lead waiting on an active leaf is not aborted as stalled", async () => {
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
        event: {
          type: "session.created",
          properties: { info: { id: "platform-architect", parentID: "meta-router" } },
        },
      })
      await hooks.event({
        event: {
          type: "session.created",
          properties: { info: { id: "terragrunt-leaf", parentID: "platform-architect" } },
        },
      })

      await sleep(1200)
      assert.equal(aborts.includes("platform-architect"), false, "lead waiting on child must survive")

      await hooks.event({
        event: { type: "permission.asked", properties: { sessionID: "platform-architect" } },
      })
    },
  )
})

test("legacy compatibility: V1 cost guard still maps message cost to the child session", async () => {
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

test("active V1 wrapper ignores stale legacy cost kill settings", async () => {
  await withEnv(
    {
      NODE_TEST_CONTEXT: undefined,
      MAX_CHILD_COST: 0.1,
      MAX_RUN_COST: 0.2,
      SUBAGENT_STALLED_TIMEOUT_SECONDS: 1,
      SUBAGENT_MAX_DURATION_SECONDS: 1,
      SUBAGENT_WATCH_INTERVAL_SECONDS: 1,
    },
    async () => {
      const { client, aborts } = makeClient()
      const hooks = await ReliabilityV1Plugin({ client })
      await hooks.event({
        event: { type: "session.created", properties: { info: { id: "cost-child", parentID: "parent" } } },
      })
      await hooks.event({
        event: {
          type: "message.updated",
          properties: {
            info: { id: "message-cost", sessionID: "cost-child", role: "assistant", cost: 999 },
          },
        },
      })
      await sleep(1200)
      assert.deepEqual(aborts, [], "stale cost env must not reactivate automatic killing")
    },
  )
})

test("WAITING_PERMISSION and post-permission silence stay fail-open in production mode", async () => {
  await withEnv(
    {
      NODE_TEST_CONTEXT: undefined,
      MAX_CHILD_COST: 0,
      MAX_RUN_COST: 0,
      SUBAGENT_HEARTBEAT_TIMEOUT_SECONDS: 1,
      SUBAGENT_STALLED_TIMEOUT_SECONDS: 1,
      SUBAGENT_MAX_DURATION_SECONDS: 2,
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
      await sleep(3200)
      assert.deepEqual(aborts, [], "heuristic silence must never auto-kill in production mode")
    },
  )
})
