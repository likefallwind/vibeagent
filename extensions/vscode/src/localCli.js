'use strict';

const childProcess = require('node:child_process');

const MAX_JSON_BYTES = 2 * 1024 * 1024;
const MAX_ERROR_BYTES = 32 * 1024;
const LOCAL_CLI_TIMEOUT_MS = 10_000;

class LocalJsonClient {
  constructor(options = {}) {
    this.spawn = options.spawn || childProcess.spawn;
    this.timeoutMs = options.timeoutMs || LOCAL_CLI_TIMEOUT_MS;
  }

  async run(config, workspaceRoot, commandArgs) {
    const args = [...config.args, '--json', '--cwd', workspaceRoot, ...commandArgs];
    const environment = { ...process.env, PYTHONUNBUFFERED: '1' };
    delete environment.VIBEAGENT_IDE_CONTEXT_FILE;
    delete environment.VIBEAGENT_IDE_CONTEXT_TOKEN;
    const child = this.spawn(config.executable, args, {
      cwd: workspaceRoot,
      env: environment,
      shell: false,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    });
    const result = await collectProcess(child, this.timeoutMs);
    return { ...result, payload: parseLocalEnvelope(result.stdout) };
  }
}

function collectProcess(child, timeoutMs) {
  return new Promise((resolve, reject) => {
    let stdout = Buffer.alloc(0);
    let stderrBytes = 0;
    let settled = false;
    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      callback(value);
    };
    const abort = (error) => {
      if (!settled && child && typeof child.kill === 'function') child.kill('SIGTERM');
      finish(reject, error);
    };
    const timer = setTimeout(
      () => abort(new Error('VibeAgent local command timed out.')),
      timeoutMs,
    );
    child.stdout.on('data', (chunk) => {
      const value = Buffer.from(chunk);
      if (stdout.length + value.length > MAX_JSON_BYTES) {
        abort(new Error('VibeAgent local command output exceeded 2 MiB.'));
        return;
      }
      stdout = Buffer.concat([stdout, value]);
    });
    child.stderr.on('data', (chunk) => {
      stderrBytes += Buffer.byteLength(chunk);
      if (stderrBytes > MAX_ERROR_BYTES) {
        abort(new Error('VibeAgent local command error output exceeded 32 KiB.'));
      }
    });
    child.on('error', (error) => abort(error));
    child.on('close', (code) => {
      finish(resolve, { code: Number.isInteger(code) ? code : -1, stdout });
    });
  });
}

function parseLocalEnvelope(raw) {
  let payload;
  try {
    payload = JSON.parse(Buffer.from(raw).toString('utf8'));
  } catch (_error) {
    throw new Error('VibeAgent returned invalid JSON from a local command.');
  }
  if (!payload || typeof payload !== 'object' || payload.schemaVersion !== 1 || payload.kind !== 'local') {
    throw new Error('VibeAgent returned an invalid local command envelope.');
  }
  return payload;
}

module.exports = {
  LOCAL_CLI_TIMEOUT_MS,
  MAX_ERROR_BYTES,
  MAX_JSON_BYTES,
  LocalJsonClient,
  collectProcess,
  parseLocalEnvelope,
};
