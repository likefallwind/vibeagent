import assert from "node:assert/strict";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { ActionParseError, parseModelAction, runCommand } from "../src/actions.js";

test("parseModelAction accepts valid write_file JSON", () => {
  const parsed = parseModelAction(
    JSON.stringify({
      thought: "create file",
      action: {
        type: "write_file",
        path: "sum.js",
        content: "console.log(5050)",
      },
    }),
  );

  assert.equal(parsed.action.type, "write_file");
  assert.equal(parsed.action.path, "sum.js");
});

test("parseModelAction rejects invalid JSON", () => {
  assert.throws(() => parseModelAction("not json"), ActionParseError);
});

test("parseModelAction rejects unsupported action", () => {
  assert.throws(
    () =>
      parseModelAction(
        JSON.stringify({
          thought: "bad",
          action: {
            type: "delete_everything",
          },
        }),
      ),
    /Unsupported action type/,
  );
});

test("runCommand captures stdout, stderr, exit code, and success", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "vibeagent-command-"));
  const result = await runCommand(cwd, "node -e \"console.log('out'); console.error('err')\"");

  assert.equal(result.exitCode, 0);
  assert.equal(result.stdout.trim(), "out");
  assert.equal(result.stderr.trim(), "err");
  assert.equal(result.timedOut, false);
});

test("runCommand reports timeout", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "vibeagent-timeout-"));
  const result = await runCommand(cwd, "node -e \"setTimeout(() => {}, 1000)\"", 50);

  assert.equal(result.timedOut, true);
  assert.notEqual(result.signal, null);
});
