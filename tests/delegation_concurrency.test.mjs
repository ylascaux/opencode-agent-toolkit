import assert from "node:assert/strict"
import test from "node:test"

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
  return {
    setChildren(next) {
      children = next
    },
    client: {
      session: {
        children: async () => ({ data: children }),
        abort: async () => {},
      },
      app: { log: async () => {} },
    },
  }
}

const taskArgs = {
  description: "Implement approved UI plan",
  prompt: "Implement the approved UI plan without replanning.",
  subagent_type: "orchestrator",
}

const startFirstTask = async (hooks, fixture) => {
  const input = { sessionID: "meta-router", tool: "task", args: { ...taskArgs } }
  await hooks["tool.execute.before"](input, { args: { ...taskArgs } })
  await hooks.event({
    event: {
      type: "session.created",
      properties: { info: { id: "orchestrator-child-1", parentID: "meta-router" } },
    },
  })
  fixture.setChildren([
    { id: "orchestrator-child-1", parentID: "meta-router", status: "RUNNING" },
  ])
  await hooks["tool.execute.after"](input, { output: "child delegated" })
}

test("identical fresh delegations are allowed when a parallel slot is available", async () => {
  await withEnv(
    {
      NODE_TEST_CONTEXT: "1",
      MAX_PARALLEL_SUBAGENTS: "2",
      SUBAGENT_QUEUE_TIMEOUT_SECONDS: "1",
      SUBAGENT_STALLED_TIMEOUT_SECONDS: "30",
      SUBAGENT_MAX_DURATION_SECONDS: "60",
      SUBAGENT_WATCH_INTERVAL_SECONDS: "1",
      MAX_CHILD_COST: "0",
      MAX_RUN_COST: "0",
    },
    async () => {
      const fixture = makeClient()
      const hooks = await ReliabilityV1Plugin({ client: fixture.client })
      await startFirstTask(hooks, fixture)

      const second = { sessionID: "meta-router", tool: "task", args: { ...taskArgs } }
      await assert.doesNotReject(() =>
        hooks["tool.execute.before"](second, { args: { ...taskArgs } }),
      )
      await hooks["tool.execute.after"](second, { output: "second child delegated" })
    },
  )
})

test("parallel slot limit, not semantic equivalence, blocks excess delegation", async () => {
  await withEnv(
    {
      NODE_TEST_CONTEXT: "1",
      MAX_PARALLEL_SUBAGENTS: "1",
      SUBAGENT_QUEUE_TIMEOUT_SECONDS: "1",
      SUBAGENT_STALLED_TIMEOUT_SECONDS: "30",
      SUBAGENT_MAX_DURATION_SECONDS: "60",
      SUBAGENT_WATCH_INTERVAL_SECONDS: "1",
      MAX_CHILD_COST: "0",
      MAX_RUN_COST: "0",
    },
    async () => {
      const fixture = makeClient()
      const hooks = await ReliabilityV1Plugin({ client: fixture.client })
      await startFirstTask(hooks, fixture)

      const second = { sessionID: "meta-router", tool: "task", args: { ...taskArgs } }
      await assert.rejects(
        () => hooks["tool.execute.before"](second, { args: { ...taskArgs } }),
        /subagent queue timed out/,
      )
    },
  )
})
