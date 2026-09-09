import assert from "node:assert/strict"
import test from "node:test"
import {
  NON_INTERACTIVE_SHELL_ENV,
  applyNonInteractiveShellEnv,
} from "../runtime/plugins/non-interactive-shell.js"
import { ReliabilityV1Plugin } from "../runtime/plugins/reliability-v1.js"

const makeClient = () => ({
  session: {
    children: async () => ({ data: [] }),
    abort: async () => {},
  },
  app: { log: async () => {} },
})

test("shared shell policy overrides interactive pager and prompt settings", () => {
  const env = {
    KEEP_ME: "yes",
    PAGER: "less",
    GIT_PAGER: "less",
    GIT_TERMINAL_PROMPT: "1",
    TF_INPUT: "1",
  }

  const result = applyNonInteractiveShellEnv(env)

  assert.equal(result, env)
  assert.equal(env.KEEP_ME, "yes")
  for (const [key, value] of Object.entries(NON_INTERACTIVE_SHELL_ENV)) {
    assert.equal(env[key], value, key)
  }
})

test("OpenCode V1 exposes the shared non-interactive shell environment", async () => {
  const hooks = await ReliabilityV1Plugin({ client: makeClient() })
  const output = { env: { PAGER: "less", KEEP_ME: "yes" } }

  assert.equal(typeof hooks["shell.env"], "function")
  await hooks["shell.env"]({}, output)

  assert.equal(output.env.KEEP_ME, "yes")
  assert.equal(output.env.PAGER, "cat")
  assert.equal(output.env.GIT_PAGER, "cat")
  assert.equal(output.env.GIT_TERMINAL_PROMPT, "0")
  assert.equal(output.env.GH_PROMPT_DISABLED, "1")
  assert.equal(output.env.TF_INPUT, "0")
  assert.equal(output.env.TF_IN_AUTOMATION, "1")
})
