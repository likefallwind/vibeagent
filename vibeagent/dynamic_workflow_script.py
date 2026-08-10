from __future__ import annotations


NODE_WORKFLOW_BRIDGE = r"""
;(async () => {
const readline = require('node:readline');
const vm = require('node:vm');

const write = (value) => process.stdout.write(JSON.stringify(value) + '\n');
const rl = readline.createInterface({input: process.stdin, crlfDelay: Infinity});
const lines = rl[Symbol.asyncIterator]();
const first = await lines.next();
if (first.done) throw new Error('missing workflow initialization');
const init = JSON.parse(first.value);
if (init.type !== 'init' || typeof init.source !== 'string') throw new Error('invalid workflow initialization');

const dispatch = (message) => write(JSON.parse(message));
const emitLog = (message) => write(JSON.parse(message));
Object.setPrototypeOf(dispatch, null);
Object.setPrototypeOf(emitLog, null);
const sandbox = Object.create(null);
Object.defineProperties(sandbox, {
  __dispatch: {value: dispatch, configurable: true},
  __emitLog: {value: emitLog, configurable: true},
});
const context = vm.createContext(sandbox, {
  name: 'vibeagent-workflow',
  codeGeneration: {strings: false, wasm: false},
});
const bootstrap = new vm.Script(`
(() => {
  const dispatch = globalThis.__dispatch;
  const emitLog = globalThis.__emitLog;
  delete globalThis.__dispatch;
  delete globalThis.__emitLog;
  let nextCall = 0;
  const pending = new Map();
  const agent = (task, options = {}) => {
    if (typeof task !== 'string' || !task.trim()) return Promise.reject(new Error('agent task must be a non-empty string'));
    if (!options || typeof options !== 'object' || Array.isArray(options)) return Promise.reject(new Error('agent options must be an object'));
    const callId = \`call-\${String(++nextCall).padStart(4, '0')}\`;
    return new Promise((resolve, reject) => {
      pending.set(callId, {resolve, reject});
      dispatch(JSON.stringify({type: 'agent', call_id: callId, task, options}));
    });
  };
  const pipeline = async (items, worker, options = {}) => {
    if (!Array.isArray(items)) throw new Error('pipeline items must be an array');
    if (typeof worker !== 'function') throw new Error('pipeline worker must be a function');
    if (items.length > 1000) throw new Error('pipeline supports at most 1000 items');
    const concurrency = options.concurrency === undefined ? 4 : options.concurrency;
    if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 16) {
      throw new Error('pipeline concurrency must be an integer between 1 and 16');
    }
    const results = new Array(items.length);
    let cursor = 0;
    const runner = async () => {
      while (true) {
        const index = cursor++;
        if (index >= items.length) return;
        results[index] = await worker(items[index], index);
      }
    };
    await Promise.all(Array.from({length: Math.min(concurrency, items.length)}, runner));
    return results;
  };
  const log = (level, values) => emitLog(JSON.stringify({type: 'log', level, values}));
  Object.defineProperties(globalThis, {
    agent: {value: Object.freeze(agent), enumerable: true},
    pipeline: {value: Object.freeze(pipeline), enumerable: true},
    console: {value: Object.freeze({
      log: (...values) => log('log', values),
      warn: (...values) => log('warn', values),
      error: (...values) => log('error', values),
    }), enumerable: true},
    __deliver: {value: (text) => {
      const message = JSON.parse(text);
      const waiter = pending.get(message.call_id);
      if (!waiter) return;
      pending.delete(message.call_id);
      if (message.ok) waiter.resolve(message.result);
      else waiter.reject(new Error(message.error || \`agent call \${message.call_id} failed\`));
    }, configurable: true},
  });
})();
`);
bootstrap.runInContext(context, {timeout: 5000});
const deliver = context.__deliver;
delete context.__deliver;
const responses = (async () => {
  for await (const line of lines) {
    const message = JSON.parse(line);
    if (message.type !== 'response' || typeof message.call_id !== 'string') continue;
    deliver(JSON.stringify(message));
  }
})();

try {
  const script = new vm.Script(`(async () => {\n${init.source}\n})()`, {filename: init.filename || 'workflow.js'});
  const result = await script.runInContext(context, {timeout: 5000});
  write({type: 'done', ok: true, result});
} catch (error) {
  write({type: 'done', ok: false, error: error && error.stack ? error.stack : String(error)});
}
await responses;
})().catch((error) => {
  process.stdout.write(JSON.stringify({type: 'done', ok: false, error: error && error.stack ? error.stack : String(error)}) + '\n');
});
"""


__all__ = ["NODE_WORKFLOW_BRIDGE"]
