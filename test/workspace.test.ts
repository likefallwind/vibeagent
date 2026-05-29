import assert from "node:assert/strict";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { createRunWorkspace, resolveInsideRun, writeRunFile } from "../src/workspace.js";

test("resolveInsideRun rejects absolute paths", async () => {
  const base = await mkdtemp(path.join(tmpdir(), "vibeagent-workspace-"));
  const workspace = await createRunWorkspace(base, "test-run");

  assert.throws(() => resolveInsideRun(workspace.root, "/tmp/file.js"), /Absolute paths/);
});

test("resolveInsideRun rejects parent directory escape", async () => {
  const base = await mkdtemp(path.join(tmpdir(), "vibeagent-workspace-"));
  const workspace = await createRunWorkspace(base, "test-run");

  assert.throws(() => resolveInsideRun(workspace.root, "../file.js"), /escapes/);
  assert.throws(() => resolveInsideRun(workspace.root, "nested/../../file.js"), /escapes/);
});

test("writeRunFile writes inside the run directory", async () => {
  const base = await mkdtemp(path.join(tmpdir(), "vibeagent-workspace-"));
  const workspace = await createRunWorkspace(base, "test-run");
  const target = await writeRunFile(workspace, "nested/hello.txt", "hello");

  assert.equal(target, path.join(workspace.root, "nested", "hello.txt"));
  assert.equal(await readFile(target, "utf8"), "hello");
});
