import assert from "node:assert/strict"
import test from "node:test"

import {
  hasActiveDelegatedChildren,
  isDelegationAlreadyRunningError,
} from "../runtime/plugins/reliability-core.js"
import { ReliabilityV1Plugin } from "../runtime/plugins/reliability-v1.js"

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
  let children = []
  const logs = []
  return {
    setChildren(next) {
      children = next
    },
    logs,
    client: {
      session: {
        children: async () => ({ data: children }),
        abort: async () => {},
      },
      app: {
        log: async (entry) => {
          logs.push(entry)
        },
      },
    },
  }
}

const taskArgs = {
  description: "Implement approved UI plan",
  prompt: "Implement the approved UI plan without replanning.",
  subagent_type: "orchestrator",
}

const prepareDelegatedTask = async (hooks, args = taskArgs) => {
  const input = { sessionID: "meta-router", tool: "task", args: { ...args } }
  await hooks["tool.execute.before"](input, { args: { ...args } })
  await hooks.event({
    event: {
      type: "session.created",
      properties: { info: { id: "orchestrator-child", parentID: "meta-router" } },
    },
  })
  await hooks["tool.execute.after"](input, { output: "child delegated" })
  return input
}

test("delegated child activity classification is conservative", () => {
  assert.equal(hasActiveDelegatedChildren([]), false)
  assert.equal(hasActiveDelegatedChildren([{ id: "done", status: "IDLE" }]), false)
  assert.equal(hasActiveDelegatedChildren([{ id: "done", status: { type: "completed" } }]), false)
  assert.equal(hasActiveDelegatedChildren([{ id: "failed", status: "FAILED" }]), false)
  assert.equal(hasActiveDelegatedChildren([{ id: "active", status: "RUNNING" }]), true)
  assert.equal(hasActiveDelegatedChildren([{ id: "unknown" }]), true)
  assert.equal(hasActiveDelegatedChildren(undefined), undefined)
})

test("only the reliability duplicate-running guard is eligible for stale recovery", () => {
  assert.equal(
    isDelegationAlreadyRunningError(
      new Error("Reliability guard: equivalent delegated task is already running (meta-router:orchestrator:ui)."),
    ),
    true,
  )
  assert.equal(isDelegationAlreadyRunningError(new Error("task already running upstream")), false)
})

test("V1 stale running delegation is released when every real child is terminal", async () => {
  await withEnv(
    {
      NODE_TEST_CONTEXT: "1",
      MAX_PARALLEL_SUBAGENTS: "2",
      SUBAGENT_QUEUE_TIMEOUT_SECONDS: "2",
      SUBAGENT_STALLED_TIMEOUT_SECONDS: "30",
      SUBAGENT_MAX_DURATION_SECONDS: "60",
      SUBAGENT_WATCH_INTERVAL_SECONDS: "1",
      MAX_CHILD_COST: "0",
      MAX_RUN_COST: "0",
    },
    async () => {
      const fixture = makeClient()
      const hooks = await ReliabilityV1Plugin({ client: fixture.client })
      await prepareDelegatedTask(hooks)

      // Reproduce the production failure: the child is terminal, but no
      // message.part.updated tool outcome arrived to move the legacy delegation
      // entry away from "running".
      fixture.setChildren([
        { id: "orchestrator-child", parentID: "meta-router", status: "IDLE" },
      ])

      const retry = { sessionID: "meta-router", tool: "task", args: { ...taskArgs } }
      await assert.doesNotReject(() => hooks["tool.execute.before"](retry, { args: { ...taskArgs } }))
      await hooks["tool.execute.after"](retry, { output: "replacement child delegated" })

      assert.equal(
        fixture.logs.some((entry) =>
          String(entry?.body?.message ?? "").includes("released stale delegation lock"),
        ),
        true,
      )
    },
  )
})

test("V1 duplicate delegation remains blocked while a real child is active", async () => {
  await withEnv(
    {
      NODE_TEST_CONTEXT: "1",
      MAX_PARALLEL_SUBAGENTS: "2",
      SUBAGENT_QUEUE_TIMEOUT_SECONDS: "2",
      SUBAGENT_STALLED_TIMEOUT_SECONDS: "30",
      SUBAGENT_MAX_DURATION_SECONDS: "60",
      SUBAGENT_WATCH_INTERVAL_SECONDS: "1",
      MAX_CHILD_COST: "0",
      MAX_RUN_COST: "0",
    },
    async () => {
      const fixture = makeClient()
      const hooks = await ReliabilityV1Plugin({ client: fixture.client })
      await prepareDelegatedTask(hooks)
      fixture.setChildren([
        { id: "orchestrator-child", parentID: "meta-router", status: "RUNNING" },
      ])

      const retry = { sessionID: "meta-router", tool: "task", args: { ...taskArgs } }
      await assert.rejects(
        () => hooks["tool.execute.before"](retry, { args: { ...taskArgs } }),
        /equivalent delegated task is already running/,
      )
    },
  )
})
