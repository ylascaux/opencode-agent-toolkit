import assert from "node:assert/strict"
import test from "node:test"
import { ReliabilityV1Plugin } from "../.opencode/plugins/reliability-v1.js"

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

const makeClient = (knownSessions = {}) => {
  const toasts = []
  const openedSessions = []
  const logs = []
  const aborts = []

  return {
    toasts,
    openedSessions,
    logs,
    aborts,
    client: {
      session: {
        children: async () => ({ data: [] }),
        get: async ({ path }) => ({ data: knownSessions[path.id] }),
        abort: async ({ path }) => {
          aborts.push(path.id)
        },
      },
      tui: {
        showToast: async (payload) => {
          toasts.push(payload)
          return true
        },
        openSessions: async () => {
          openedSessions.push(true)
          return true
        },
      },
      app: {
        log: async (payload) => {
          logs.push(payload)
          return true
        },
      },
    },
  }
}

test("V1 permission bridge surfaces a delegated ASK without auto-approving it", async () => {
  await withEnv(
    {
      NODE_TEST_CONTEXT: "1",
      PERMISSION_BRIDGE_TOAST: "1",
      PERMISSION_BRIDGE_OPEN_SESSIONS: "1",
      MAX_CHILD_COST: 0,
      MAX_RUN_COST: 0,
    },
    async () => {
      const { client, toasts, openedSessions } = makeClient()
      const hooks = await ReliabilityV1Plugin({ client })

      await hooks.event({
        event: {
          type: "session.created",
          properties: {
            info: {
              id: "ses_child_1234567890",
              parentID: "ses_parent",
              agent: "terraform-terragrunt",
            },
          },
        },
      })

      const ask = {
        type: "permission.asked",
        properties: {
          id: "per_123",
          sessionID: "ses_child_1234567890",
          permission: "bash",
          patterns: ["rg -n TODO ."],
        },
      }

      await hooks.event({ event: ask })

      assert.equal(toasts.length, 1)
      assert.equal(openedSessions.length, 1)
      assert.equal(toasts[0].body.title, "Subagent permission required")
      assert.match(toasts[0].body.message, /terraform-terragrunt/)
      assert.match(toasts[0].body.message, /bash: rg -n TODO \./)
      assert.equal(toasts[0].body.variant, "warning")

      // Replaying the exact same event must not spam the TUI.
      await hooks.event({ event: ask })
      assert.equal(toasts.length, 1)
      assert.equal(openedSessions.length, 1)
    },
  )
})

test("V1 permission bridge leaves root-session ASK handling to native OpenCode", async () => {
  await withEnv(
    {
      NODE_TEST_CONTEXT: "1",
      PERMISSION_BRIDGE_TOAST: "1",
      PERMISSION_BRIDGE_OPEN_SESSIONS: "1",
      MAX_CHILD_COST: 0,
      MAX_RUN_COST: 0,
    },
    async () => {
      const { client, toasts, openedSessions } = makeClient()
      const hooks = await ReliabilityV1Plugin({ client })

      await hooks.event({
        event: {
          type: "permission.asked",
          properties: {
            id: "per_root",
            sessionID: "ses_root",
            permission: "edit",
            patterns: ["README.md"],
          },
        },
      })

      assert.deepEqual(toasts, [])
      assert.deepEqual(openedSessions, [])
    },
  )
})

test("V1 permission bridge resolves parentage through session.get when creation was missed", async () => {
  await withEnv(
    {
      NODE_TEST_CONTEXT: "1",
      PERMISSION_BRIDGE_TOAST: "1",
      PERMISSION_BRIDGE_OPEN_SESSIONS: "1",
      MAX_CHILD_COST: 0,
      MAX_RUN_COST: 0,
    },
    async () => {
      const { client, toasts, openedSessions } = makeClient({
        ses_hidden_child: {
          id: "ses_hidden_child",
          parentID: "ses_parent",
          agent: "tester",
        },
      })
      const hooks = await ReliabilityV1Plugin({ client })

      await hooks.event({
        event: {
          type: "permission.asked",
          properties: {
            id: "per_hidden",
            sessionID: "ses_hidden_child",
            permission: "bash",
            patterns: ["pytest -q"],
          },
        },
      })

      assert.equal(toasts.length, 1)
      assert.equal(openedSessions.length, 1)
      assert.match(toasts[0].body.message, /tester/)
      assert.match(toasts[0].body.message, /pytest -q/)
    },
  )
})

test("V1 permission bridge can disable automatic session selector opening", async () => {
  await withEnv(
    {
      NODE_TEST_CONTEXT: "1",
      PERMISSION_BRIDGE_TOAST: "1",
      PERMISSION_BRIDGE_OPEN_SESSIONS: "0",
      MAX_CHILD_COST: 0,
      MAX_RUN_COST: 0,
    },
    async () => {
      const { client, toasts, openedSessions } = makeClient()
      const hooks = await ReliabilityV1Plugin({ client })

      await hooks.event({
        event: {
          type: "session.created",
          properties: { info: { id: "ses_child", parentID: "ses_parent", agent: "builder" } },
        },
      })
      await hooks.event({
        event: {
          type: "permission.asked",
          properties: {
            id: "per_child",
            sessionID: "ses_child",
            permission: "edit",
            patterns: ["src/main.ts"],
          },
        },
      })

      assert.equal(toasts.length, 1)
      assert.deepEqual(openedSessions, [])
    },
  )
})
