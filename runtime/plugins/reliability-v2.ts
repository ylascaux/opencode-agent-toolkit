import { applyNonInteractiveShellEnv } from "./non-interactive-shell.js"
import legacy from "./reliability-v2-legacy.ts"

const FAIL_OPEN_OVERRIDES = {
  MAX_CHILD_COST: "0",
  MAX_RUN_COST: "0",
  SUBAGENT_STALLED_TIMEOUT_SECONDS: "2147483647",
  SUBAGENT_MAX_DURATION_SECONDS: "2147483647",
  MAX_SAME_ERROR: "2147483647",
}

export default {
  ...(legacy as any),
  async setup(ctx: any) {
    if (typeof ctx.shell?.hook !== "function") {
      throw new Error("OpenCode V2 shell create.before hook is required for non-interactive agent execution")
    }

    const shellRegistration = await ctx.shell.hook("create.before", async (event: any) => {
      event.env ??= {}
      applyNonInteractiveShellEnv(event.env)
    })

    const previous = new Map<string, string | undefined>()
    for (const [key, value] of Object.entries(FAIL_OPEN_OVERRIDES)) {
      previous.set(key, process.env[key])
      process.env[key] = value
    }

    let legacyCleanup: unknown
    try {
      const setup = (legacy as any)?.setup
      if (typeof setup !== "function") throw new Error("Legacy V2 reliability plugin does not expose setup()")
      legacyCleanup = await setup(ctx)
    } catch (error) {
      const dispose = (shellRegistration as any)?.dispose
      if (typeof dispose === "function") await dispose.call(shellRegistration)
      throw error
    } finally {
      for (const [key, value] of previous.entries()) {
        if (value === undefined) delete process.env[key]
        else process.env[key] = value
      }
    }

    return async () => {
      if (typeof legacyCleanup === "function") await legacyCleanup()
      const dispose = (shellRegistration as any)?.dispose
      if (typeof dispose === "function") await dispose.call(shellRegistration)
    }
  },
}
