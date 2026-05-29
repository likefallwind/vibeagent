import assert from "node:assert/strict";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { runAgent } from "../src/agent.js";
import type { ChatClient, ChatMessage } from "../src/types.js";

class MockClient implements ChatClient {
  private index = 0;

  constructor(private readonly responses: string[]) {}

  async complete(_messages: ChatMessage[]): Promise<string> {
    const response = this.responses[this.index];
    this.index += 1;
    if (!response) {
      throw new Error("No mock response available.");
    }
    return response;
  }
}

test("runAgent repairs a failing script and finishes", async () => {
  const base = await mkdtemp(path.join(tmpdir(), "vibeagent-agent-"));
  const client = new MockClient([
    JSON.stringify({
      thought: "write an initial script",
      action: {
        type: "write_file",
        path: "sum.js",
        content: "console.log(total)",
      },
    }),
    JSON.stringify({
      thought: "run it",
      action: {
        type: "run_command",
        command: "node sum.js",
      },
    }),
    JSON.stringify({
      thought: "fix missing variable",
      action: {
        type: "write_file",
        path: "sum.js",
        content: "const total = Array.from({ length: 100 }, (_, i) => i + 1).reduce((a, b) => a + b, 0); console.log(total);",
      },
    }),
    JSON.stringify({
      thought: "run fixed script",
      action: {
        type: "run_command",
        command: "node sum.js",
      },
    }),
    JSON.stringify({
      thought: "done",
      action: {
        type: "finish",
        message: "Generated and ran sum.js successfully.",
      },
    }),
  ]);

  const result = await runAgent("sum 1 to 100", {
    baseDir: base,
    client,
    maxIterations: 5,
  });

  assert.equal(result.success, true);
  assert.match(result.runDir, /\.vibeagent\/runs\//);
  assert.equal(result.observations.filter((item) => item.kind === "run_command").length, 2);

  const commandObservations = result.observations.filter((item) => item.kind === "run_command");
  const failed = commandObservations[0];
  const succeeded = commandObservations[1];
  assert.equal(failed.kind, "run_command");
  assert.notEqual(failed.result.exitCode, 0);
  assert.equal(succeeded.kind, "run_command");
  assert.equal(succeeded.result.exitCode, 0);
  assert.equal(succeeded.result.stdout.trim(), "5050");
});
