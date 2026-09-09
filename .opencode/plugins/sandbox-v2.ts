import path from "node:path"
import { fileURLToPath } from "node:url"
import { Plugin } from "@opencode/plugin"

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..")
const RUNNER = path.join(ROOT, "scripts", "sandbox-run")

const enabled = () => process.env.OAT_SANDBOX_ENABLED === "1"
const quote = (value: string) => `'${value.replaceAll("'", `'"'"'`)}'`

export default Plugin.define({
  id: "agent-sandbox-v2",
  async setup(ctx) {
    await ctx.shell.hook("create.before", (event) => {
      if (!enabled()) return
      const original = event.command
      event.command = `bash ${quote(RUNNER)} --cwd ${quote(event.cwd)} --command ${quote(original)}`
    })
  },
})
