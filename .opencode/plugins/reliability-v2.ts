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
    const previous = new Map<string, string | undefined>()
    for (const [key, value] of Object.entries(FAIL_OPEN_OVERRIDES)) {
      previous.set(key, process.env[key])
      process.env[key] = value
    }
    try {
      const setup = (legacy as any)?.setup
      if (typeof setup !== "function") throw new Error("Legacy V2 reliability plugin does not expose setup()")
      return await setup(ctx)
    } finally {
      for (const [key, value] of previous.entries()) {
        if (value === undefined) delete process.env[key]
        else process.env[key] = value
      }
    }
  },
}
