'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { AgentChangeContentProvider, MAX_TRACKED_DOCUMENTS } = require('../src/agentChanges');

test('change provider keeps bounded in-memory virtual documents', () => {
  class EventEmitter {
    constructor() { this.event = () => ({ dispose() {} }); }
    dispose() { this.disposed = true; }
  }
  const vscode = {
    EventEmitter,
    Uri: {
      parse(value) { return { value, toString() { return value; } }; },
    },
  };
  const provider = new AgentChangeContentProvider(vscode);
  const first = provider.track('src/first.py', 'base', 'first\n');
  let newest;
  for (let index = 0; index < MAX_TRACKED_DOCUMENTS; index += 1) {
    newest = provider.track(`src/file-${index}.py`, 'current', `${index}\n`);
  }

  assert.throws(() => provider.provideTextDocumentContent(first), /no longer available/);
  assert.equal(provider.provideTextDocumentContent(newest), `${MAX_TRACKED_DOCUMENTS - 1}\n`);
  provider.dispose();
  assert.throws(() => provider.provideTextDocumentContent(newest), /no longer available/);
});
