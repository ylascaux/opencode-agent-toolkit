import assert from "node:assert/strict"
import test from "node:test"

import {
  PLAN_REAPPROVAL_MARKER,
  PLAN_REQUIRED_MARKER,
  createPlanApprovalGate,
  isApprovalMessage,
  isReadOnlyShellCommand,
  isRejectionMessage,
  normalizePlanApprovalMode,
  toolRequiresPlanApproval,
} from "../.opencode/plugins/plan-approval-core.js"

test("approval mode normalization is conservative", () => {
  assert.equal(normalizePlanApprovalMode("changes"), "changes")
  assert.equal(normalizePlanApprovalMode("always"), "always")
  assert.equal(normalizePlanApprovalMode("off"), "off")
  assert.equal(normalizePlanApprovalMode("bogus"), "changes")
})

test("approval and rejection require explicit short responses", () => {
  for (const value of ["go", "approve", "oui", "valide", "exécute le plan"]) {
    assert.equal(isApprovalMessage(value), true, value)
  }
  for (const value of ["non", "reject", "stop", "annule"]) {
    assert.equal(isRejectionMessage(value), true, value)
  }
  assert.equal(isApprovalMessage("go mais sans les tests"), false)
  assert.equal(isApprovalMessage("okay change one more file first"), false)
})

test("shell classifier allows read-only evidence and blocks hidden mutation", () => {
  for (const command of [
    "git status",
    "git --no-pager diff --stat",
    "rg -n TODO . | wc -l",
    "terraform plan",
    "kubectl get pods",
    "pytest -q",
  ]) {
    assert.equal(isReadOnlyShellCommand(command), true, command)
  }
  for (const command of [
    "git add .",
    "printf x > file.txt",
    "rg foo && rm file.txt",
    "find . -delete",
    "python3 -c 'open(\"x\",\"w\").write(\"x\")'",
  ]) {
    assert.equal(isReadOnlyShellCommand(command), false, command)
  }
})

test("changes mode blocks mutators and implementation delegation but keeps planning available", () => {
  assert.equal(toolRequiresPlanApproval("read", {}, "changes"), false)
  assert.equal(toolRequiresPlanApproval("bash", { command: "git status" }, "changes"), false)
  assert.equal(toolRequiresPlanApproval("write", {}, "changes"), true)
  assert.equal(toolRequiresPlanApproval("bash", { command: "git add ." }, "changes"), true)
  assert.equal(toolRequiresPlanApproval("task", { subagent_type: "planner" }, "changes"), false)
  assert.equal(toolRequiresPlanApproval("task", { subagent_type: "project-scanner" }, "changes"), false)
  assert.equal(toolRequiresPlanApproval("task", { subagent_type: "builder" }, "changes"), true)
})

test("always mode keeps direct discovery available but gates delegation", () => {
  assert.equal(toolRequiresPlanApproval("read", {}, "always"), false)
  assert.equal(toolRequiresPlanApproval("websearch", {}, "always"), false)
  assert.equal(toolRequiresPlanApproval("task", { subagent_type: "planner" }, "always"), true)
})

test("approved plan propagates to children and resets on the next root user turn", () => {
  const gate = createPlanApprovalGate({ mode: "changes" })
  gate.onUserMessage("root", "fix the bug", "u1")
  gate.onAssistantText("child", `Plan\n${PLAN_REQUIRED_MARKER}`, "a1")
  // Parent relation can arrive after the child produced its plan; state must merge upward.
  gate.rememberParent("child", "root")
  assert.equal(gate.state("root").status, "waiting")

  gate.onUserMessage("root", "go", "u2")
  assert.equal(gate.state("root").status, "approved")
  assert.equal(gate.beforeTool("child", "write", {}).allowed, true)

  gate.onUserMessage("root", "also update the docs", "u3")
  assert.equal(gate.state("root").status, "planning")
  assert.equal(gate.beforeTool("child", "write", {}).allowed, false)
})

test("runtime block creates a waiting gate and rejection cannot be bypassed", () => {
  const gate = createPlanApprovalGate({ mode: "changes" })
  gate.onUserMessage("root", "change it", "u1")
  const blocked = gate.beforeTool("root", "edit", {})
  assert.equal(blocked.allowed, false)
  assert.equal(gate.state("root").status, "waiting")

  gate.onUserMessage("root", "non", "u2")
  assert.equal(gate.state("root").status, "rejected")
  assert.equal(gate.beforeTool("root", "edit", {}).allowed, false)
})

test("scope deviation revokes an existing approval until reapproved", () => {
  const gate = createPlanApprovalGate({ mode: "changes" })
  gate.onUserMessage("root", "change it", "u1")
  gate.onAssistantText("root", `Plan\n${PLAN_REQUIRED_MARKER}`, "a1")
  gate.onUserMessage("root", "approve", "u2")
  assert.equal(gate.beforeTool("root", "write", {}).allowed, true)

  gate.onAssistantText("root", `New dependency found\n${PLAN_REAPPROVAL_MARKER}`, "a2")
  assert.equal(gate.state("root").status, "waiting")
  assert.equal(gate.beforeTool("root", "write", {}).allowed, false)

  gate.onUserMessage("root", "oui", "u3")
  assert.equal(gate.beforeTool("root", "write", {}).allowed, true)
})
