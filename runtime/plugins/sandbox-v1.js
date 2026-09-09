import path from "node:path"
import { fileURLToPath } from "node:url"

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..")
const RUNNER = path.join(ROOT, "scripts", "sandbox-run")
const quote = (value) => `'${String(value).replaceAll("'", `'"'"'`)}'`

export const SandboxV1 = async ({ directory }) => ({
  "tool.execute.before": async (input, output) => {
    if (process.env.OAT_SANDBOX_ENABLED !== "1" || input.tool !== "bash") return
    const original = String(output.args?.command ?? "")
    if (!original) return
    const requestedCwd = output.args?.workdir ?? output.args?.cwd ?? directory
    const cwd = path.isAbsolute(requestedCwd)
      ? requestedCwd
      : path.resolve(directory, requestedCwd)
    output.args.command = `bash ${quote(RUNNER)} --cwd ${quote(cwd)} --command ${quote(original)}`
    delete output.args.workdir
    delete output.args.cwd
  },
})
