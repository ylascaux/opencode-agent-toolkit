export const stableString = (value) => {
  const sorted = (input) => {
    if (Array.isArray(input)) return input.map(sorted)
    if (input && typeof input === "object") {
      return Object.fromEntries(Object.keys(input).sort().map((key) => [key, sorted(input[key])]))
    }
    return input
  }
  try {
    return JSON.stringify(sorted(value))
  } catch {
    return String(value)
  }
}

export const createCallIdTracker = () => {
  let sequence = 0
  const queues = new Map()

  const signature = ({ sessionID, tool, args }) =>
    `${sessionID ?? "unknown"}:${tool ?? "tool"}:${stableString(args ?? {})}`

  const begin = ({ nativeID, sessionID, tool, args }) => {
    if (nativeID) return nativeID
    const key = signature({ sessionID, tool, args })
    const callID = `${key}:fallback-${++sequence}`
    const queue = queues.get(key) ?? []
    queue.push(callID)
    queues.set(key, queue)
    return callID
  }

  const end = ({ nativeID, sessionID, tool, args }) => {
    if (nativeID) return nativeID
    const key = signature({ sessionID, tool, args })
    const queue = queues.get(key) ?? []
    const callID = queue.shift()
    if (queue.length > 0) queues.set(key, queue)
    else queues.delete(key)
    return callID ?? `${key}:unmatched`
  }

  const pending = ({ sessionID, tool, args }) => {
    const key = signature({ sessionID, tool, args })
    return [...(queues.get(key) ?? [])]
  }

  return { begin, end, pending }
}

export const createProgressAwareRepeatDetector = () => {
  const epochs = new Map()
  const history = new Map()

  const epochFor = (sessionID) => epochs.get(sessionID) ?? 0

  const markProgress = (sessionID) => {
    if (!sessionID) return
    epochs.set(sessionID, epochFor(sessionID) + 1)
  }

  const observe = ({ sessionID, tool, args, result, failed = false }) => {
    const key = `${sessionID}:${tool}`
    const epoch = epochFor(sessionID)
    const previous = history.get(key)
    const same = Boolean(
      previous &&
      previous.epoch === epoch &&
      previous.args === args &&
      previous.result === result &&
      result,
    )
    const count = same ? previous.count + 1 : 1

    // A successful distinct outcome is material progress. Advance the epoch
    // before storing the new baseline so later identical calls are compared
    // only within the new progress window.
    if (!failed && !same) markProgress(sessionID)
    history.set(key, {
      args,
      result,
      count,
      epoch: epochFor(sessionID),
    })
    return { same, count }
  }

  return { markProgress, observe, epochFor }
}

export const createStallDetector = () => {
  const suspects = new Map()

  const clear = (sessionID) => {
    if (sessionID) suspects.delete(sessionID)
  }

  const observe = ({
    sessionID,
    timestamp,
    lastActivityAt,
    lastProgressAt,
    heartbeatMs,
    stalledMs,
    confirmationMs = 0,
    busy = false,
  }) => {
    if (!sessionID) return { stalled: false, suspect: false }

    const noHeartbeat = timestamp - lastActivityAt > heartbeatMs
    const noProgress = timestamp - lastProgressAt > stalledMs
    if (busy || !noHeartbeat || !noProgress) {
      clear(sessionID)
      return { stalled: false, suspect: false }
    }

    const previous = suspects.get(sessionID)
    if (
      !previous ||
      previous.lastActivityAt !== lastActivityAt ||
      previous.lastProgressAt !== lastProgressAt
    ) {
      suspects.set(sessionID, { since: timestamp, lastActivityAt, lastProgressAt })
      return { stalled: false, suspect: true }
    }

    if (timestamp - previous.since < confirmationMs) return { stalled: false, suspect: true }

    clear(sessionID)
    return { stalled: true, suspect: false }
  }

  return { observe, clear }
}

export const providerRetryDecision = ({ status, attempt, maxRetries }) => {
  if ([400, 401, 403, 404].includes(status ?? 0)) return { retry: false }
  if (attempt > maxRetries + 1) return { retry: false }
  if (status === 429 || (status !== undefined && status >= 500)) {
    return { retry: true, delay: Math.min(10_000, 1000 * attempt) }
  }
  return undefined
}

export const delegationFailureClass = (value) => {
  const text = String(value ?? "").toLowerCase()
  if (
    /\b(400|401|403|404)\b|unauth|forbidden|invalid[ -]?request|model.+not found|credential|permission denied|not permitted|unknown agent|depth limit/.test(
      text,
    )
  ) {
    return "terminal"
  }
  if (
    /task cancel(?:led|ed)|\bcancel(?:led|ed)\b|\babort(?:ed)?\b|no-material-progress|max-duration-exceeded|timed? out|timeout|child disappeared|session ended unexpectedly|connection reset|temporar/.test(
      text,
    )
  ) {
    return "retryable"
  }
  return "unknown"
}

export const delegationTaskKey = ({ parentID, args }) => {
  const type = String(args?.subagent_type ?? args?.agent ?? args?.type ?? "subagent").trim().toLowerCase()
  const description = String(args?.description ?? "").trim().toLowerCase()
  const prompt = String(args?.prompt ?? "").trim().toLowerCase().replace(/\s+/g, " ")
  const scope = description || prompt.slice(0, 240) || "unnamed"
  return `${parentID ?? "unknown"}:${type}:${scope}`
}
