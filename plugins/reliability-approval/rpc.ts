import { Rpc } from "@opencode/plugin/rpc"

export const ReliabilityApproval = Rpc.define({
  id: "agent-reliability-approval",
  methods: {
    decide: {
      input: {
        type: "object",
        properties: {
          sessionID: { type: "string" },
          action: { type: "string", enum: ["kill", "keep"] },
        },
        required: ["sessionID", "action"],
        additionalProperties: false,
      },
      output: {
        type: "object",
        properties: {
          status: { type: "string", enum: ["killed", "kept", "stale", "unknown"] },
        },
        required: ["status"],
        additionalProperties: false,
      },
    },
  },
  events: {
    suspected: {
      schema: {
        type: "object",
        properties: {
          sessionID: { type: "string" },
          parentID: { type: "string" },
          agent: { type: "string" },
          reason: { type: "string", enum: ["no-observable-progress", "max-duration"] },
          ageSeconds: { type: "number" },
          noActivitySeconds: { type: "number" },
          noProgressSeconds: { type: "number" },
        },
        required: [
          "sessionID",
          "parentID",
          "agent",
          "reason",
          "ageSeconds",
          "noActivitySeconds",
          "noProgressSeconds",
        ],
        additionalProperties: false,
      },
    },
  },
})
