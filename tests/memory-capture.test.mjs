import assert from "node:assert/strict"
import test from "node:test"
import { buildPrompt, containsSecret, extractJson, fingerprint, transcriptFromContext, validateCandidates } from "../runtime/plugins/memory-capture-core.js"

test("transcript keeps only user and assistant text", () => {
  const text = transcriptFromContext([
    { type: "user", text: "Prefer just over make." },
    { type: "assistant", content: [{ type: "reasoning", text: "hidden" }, { type: "text", text: "Understood." }] },
    { type: "shell", command: "rm -rf /" },
  ], 1000)
  assert.match(text, /USER:\nPrefer just over make\./)
  assert.match(text, /ASSISTANT:\nUnderstood\./)
  assert.doesNotMatch(text, /hidden|rm -rf/)
})

test("candidate validation rejects secrets and low confidence", () => {
  const candidates = validateCandidates({ candidates: [
    { kind: "workstyle", title: "Use just", statement: "Prefer justfiles for developer commands", confidence: "high" },
    { kind: "decision", title: "Bad", statement: "token=supersecretvalue123", confidence: "high" },
    { kind: "decision", title: "Maybe", statement: "Possibly use Redis", confidence: "low" },
  ] }, 5)
  assert.equal(candidates.length, 1)
  assert.equal(candidates[0].kind, "workstyle")
  assert.equal(containsSecret("AKIA1234567890ABCDEF"), true)
})

test("extractor JSON accepts fenced JSON and fingerprint is deterministic", () => {
  const payload = extractJson('```json\n{"candidates":[]}\n```')
  assert.deepEqual(payload, { candidates: [] })
  const candidate = { kind: "decision", title: "Memory", statement: "Keep durable memory in Git", confidence: "high" }
  assert.equal(fingerprint("repo", candidate), fingerprint("repo", candidate))
})

test("extractor prompt is conservative about raw transcripts and secrets", () => {
  const prompt = buildPrompt("repo", "repo", "USER:\nhello")
  assert.match(prompt, /Prefer zero candidates over a bad candidate/)
  assert.match(prompt, /Never include credentials, secrets, tokens/)
})
