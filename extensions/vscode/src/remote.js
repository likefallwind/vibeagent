'use strict';

const childProcess = require('node:child_process');
const http = require('node:http');

const MAX_RESPONSE_BYTES = 1024 * 1024;
const MAX_STARTUP_OUTPUT_CHARS = 16_000;
const STARTUP_TIMEOUT_MS = 10_000;
const REQUEST_TIMEOUT_MS = 5_000;

function parseRemoteControlUrl(value) {
  let parsed;
  try {
    parsed = new URL(value);
  } catch (_error) {
    throw new Error('VibeAgent returned an invalid Remote Control URL.');
  }
  const token = new URLSearchParams(parsed.hash.slice(1)).get('token');
  if (
    parsed.protocol !== 'http:'
    || parsed.hostname !== '127.0.0.1'
    || parsed.pathname !== '/'
    || parsed.username
    || parsed.password
    || !parsed.port
    || !token
    || token.length < 32
    || token.length > 256
  ) {
    throw new Error('VibeAgent Remote Control must use an authenticated 127.0.0.1 URL.');
  }
  return { baseUrl: `${parsed.origin}/`, token };
}

function requestJson(baseUrl, token, method, apiPath, payload, requestImpl = http.request) {
  const url = new URL(apiPath, baseUrl);
  if (url.origin !== new URL(baseUrl).origin || !url.pathname.startsWith('/api/')) {
    return Promise.reject(new Error('Remote Control API path is invalid.'));
  }
  const body = payload === undefined ? null : Buffer.from(JSON.stringify(payload), 'utf8');
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      callback(value);
    };
    const request = requestImpl(url, {
      method,
      agent: false,
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
        ...(body ? { 'Content-Type': 'application/json', 'Content-Length': String(body.length) } : {}),
      },
    }, (response) => {
      const chunks = [];
      let size = 0;
      response.on('data', (chunk) => {
        size += chunk.length;
        if (size > MAX_RESPONSE_BYTES) {
          request.destroy(new Error('Remote Control response exceeded 1 MiB.'));
          return;
        }
        chunks.push(chunk);
      });
      response.on('end', () => {
        let result;
        try {
          result = JSON.parse(Buffer.concat(chunks).toString('utf8'));
        } catch (_error) {
          finish(reject, new Error('Remote Control returned invalid JSON.'));
          return;
        }
        if (response.statusCode < 200 || response.statusCode >= 300) {
          const message = result && typeof result.error === 'string'
            ? result.error
            : `Remote Control request failed with status ${response.statusCode}.`;
          finish(reject, new Error(message));
          return;
        }
        finish(resolve, result);
      });
    });
    request.setTimeout(REQUEST_TIMEOUT_MS, () => request.destroy(new Error('Remote Control request timed out.')));
    request.on('error', (error) => finish(reject, error));
    if (body) request.write(body);
    request.end();
  });
}

class RemoteControlClient {
  constructor(baseUrl, token, requestImpl) {
    this.baseUrl = baseUrl;
    this.token = token;
    this.requestImpl = requestImpl;
  }

  get(apiPath) {
    return requestJson(this.baseUrl, this.token, 'GET', apiPath, undefined, this.requestImpl);
  }

  post(apiPath, payload) {
    return requestJson(this.baseUrl, this.token, 'POST', apiPath, payload, this.requestImpl);
  }
}

class RemoteControlProcess {
  constructor(options = {}) {
    this.spawn = options.spawn || childProcess.spawn;
    this.requestImpl = options.requestImpl;
    this.startupTimeoutMs = options.startupTimeoutMs || STARTUP_TIMEOUT_MS;
    this.child = null;
    this.client = null;
  }

  start(config, workspaceRoot, extraEnvironment = {}) {
    if (this.child) return Promise.reject(new Error('Remote Control is already running.'));
    const args = [
      ...config.args,
      'remote-control',
      '--cwd',
      workspaceRoot,
      '--remote-control-port',
      '0',
    ];
    const child = this.spawn(config.executable, args, {
      cwd: workspaceRoot,
      env: { ...process.env, ...extraEnvironment, PYTHONUNBUFFERED: '1' },
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    });
    this.child = child;
    return new Promise((resolve, reject) => {
      let output = '';
      let settled = false;
      const finish = (callback, value) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        callback(value);
      };
      const timer = setTimeout(() => {
        this.dispose();
        finish(reject, new Error('VibeAgent Remote Control did not start within 10 seconds.'));
      }, this.startupTimeoutMs);
      child.stdout.on('data', (chunk) => {
        output = `${output}${chunk.toString('utf8')}`.slice(-MAX_STARTUP_OUTPUT_CHARS);
        const match = output.match(/(?:^|\n)\s*open:\s*(\S+)/);
        if (!match) return;
        try {
          const connection = parseRemoteControlUrl(match[1]);
          this.client = new RemoteControlClient(connection.baseUrl, connection.token, this.requestImpl);
          finish(resolve, this.client);
        } catch (error) {
          this.dispose();
          finish(reject, error);
        }
      });
      child.stderr.on('data', () => {});
      child.on('error', (error) => {
        this.dispose();
        finish(reject, error);
      });
      child.on('exit', (code) => {
        if (!settled) {
          this.child = null;
          finish(reject, new Error(`VibeAgent Remote Control exited during startup (${code}).`));
        }
      });
    });
  }

  dispose() {
    const child = this.child;
    this.child = null;
    this.client = null;
    if (child && !child.killed) {
      child.kill('SIGTERM');
      const forceKill = setTimeout(() => {
        if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');
      }, 1_000);
      forceKill.unref();
      child.once('exit', () => clearTimeout(forceKill));
    }
  }
}

module.exports = {
  MAX_RESPONSE_BYTES,
  RemoteControlClient,
  RemoteControlProcess,
  parseRemoteControlUrl,
  requestJson,
};
