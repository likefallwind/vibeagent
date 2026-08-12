'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { IdeContextBridge } = require('../src/context');

test('publishes and removes one private discoverable IDE connection', () => {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'vibeagent-context-test-'));
  const root = path.join(base, 'project');
  const registry = path.join(base, 'registry');
  fs.mkdirSync(root);
  const bridge = new IdeContextBridge(root, { registryRoot: registry });
  try {
    const files = fs.readdirSync(registry).filter((name) => name.endsWith('.json'));
    assert.equal(files.length, 1);
    const connection = JSON.parse(fs.readFileSync(path.join(registry, files[0]), 'utf8'));
    assert.equal(connection.version, 1);
    assert.equal(connection.workspaceRoot, path.resolve(root));
    assert.equal(connection.contextFile, bridge.environment().VIBEAGENT_IDE_CONTEXT_FILE);
    assert.equal(connection.token, bridge.environment().VIBEAGENT_IDE_CONTEXT_TOKEN);
    if (process.platform !== 'win32') {
      assert.equal(fs.statSync(registry).mode & 0o777, 0o700);
      assert.equal(fs.statSync(path.join(registry, files[0])).mode & 0o777, 0o600);
    }
  } finally {
    bridge.dispose();
    assert.deepEqual(fs.readdirSync(registry), []);
    fs.rmSync(base, { recursive: true, force: true });
  }
});
