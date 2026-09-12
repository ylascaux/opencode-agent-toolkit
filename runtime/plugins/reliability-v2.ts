import { applyNonInteractiveShellEnv } from "./non-interactive-shell.js"
import legacy from "./reliability-v2-legacy.ts"
import {
  hasActiveDelegatedChildren,
  isDelegationAlreadyRunningError,
} from "./reliability-core.js"

const FAIL_OPEN_OVERRIDES = {
  MAX_CHILD_COST: "0",
  MAX_RUN_COST: "0",
  SUBAGENT_STALLED_TIMEOUT_SECONDS: "2147483647",
  SUBAGENT_MAX_DURATION_SECONDS: "2147483647",
  MAX_SAME_ERROR: "2147483647",
}

const unwrap = (value: any) => value?.data ?? value

const activeDelegatedChildren = async (ctx: any, sessionID?: string) => {
  if (!sessionID || typeof ctx?.session?.children !== "function") return undefined
  try {
    let result: any
    try {
      result = await ctx.session.children({ sessionID })
    } catch {
      result = await ctx.session.children({ path: { id: sessionID } })
    }
    return hasActiveDelegatedChildren(unwrap(result) ?? [])
  } catch {
    // Unknown state must fail closed: only release a stale lock after a successful children lookup.
    return undefined
  }
}

const legacyContextWithStaleDelegationRecovery = (ctx: any) => {
  if (typeof ctx?.tool?.hook !== "function") return ctx

  const wrappedCtx = Object.create(ctx)
  const wrappedTool = Object.create(ctx.tool)
  const originalHook = ctx.tool.hook.bind(ctx.tool)

  wrappedTool.hook = async (name: string, handler: (event: any) => unknown) => {
    if (name !== "execute.before") return originalHook(name, handler)
    return originalHook(name, async (event: any) => {
      try {
        return await handler(event)
      } catch (error) {
        if (!isDelegationAlreadyRunningError(error)) throw error
        const sessionID = event?.sessionID ?? event?.sessionId
        const active = await activeDelegatedChildren(ctx, sessionID)
        if (active !== false) throw error
        console.warn(`[agent-reliability] released stale delegation lock for ${sessionID ?? "unknown"}: no active child`)
        // The legacy delegation map is intentionally not mutated from the
        // compatibility wrapper. Allow this one task to proceed; its real child
        // outcome will reconcile the existing entry. If child state is unknown
        // or active, preserve the original guard error.
        return
      }
    })
  }

  wrappedCtx.tool = wrappedTool
  return wrappedCtx
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
      legacyCleanup = await setup(legacyContextWithStaleDelegationRecovery(ctx))
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
