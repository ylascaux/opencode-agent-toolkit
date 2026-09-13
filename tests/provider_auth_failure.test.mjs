import assert from "node:assert/strict"
import test from "node:test"
import { delegationFailureClass } from "../runtime/plugins/reliability-core.js"

test("expired provider authentication is terminal and must not be retried", () => {
  assert.equal(delegationFailureClass("Provided authentication token is expired."), "terminal")
  assert.equal(delegationFailureClass("OAuth access token expired"), "terminal")
  assert.equal(delegationFailureClass("authentication token is invalid"), "terminal")
  assert.equal(delegationFailureClass("Task cancelled"), "retryable")
})
