from __future__ import annotations


REMOTE_CONTROL_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VibeAgent Remote Control</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <header>
    <div class="brand-mark" aria-hidden="true">VA</div>
    <div>
      <h1>VibeAgent Remote Control</h1>
      <p id="project">Connecting...</p>
    </div>
    <span id="connection" class="status-pill">Offline</span>
  </header>
  <main>
    <section class="roster" aria-label="Background agents">
      <div class="section-head">
        <div>
          <h2>Agents</h2>
          <p id="summary">No state loaded</p>
        </div>
        <button id="refresh" class="icon-button" title="Refresh" aria-label="Refresh">&#8635;</button>
      </div>
      <form id="dispatch-form" class="command-row">
        <input id="dispatch-task" maxlength="8000" placeholder="Dispatch a coding task" required>
        <button type="submit">Dispatch</button>
      </form>
      <div id="agents" class="agent-list"></div>
    </section>
    <section class="detail" aria-label="Selected agent">
      <div id="empty-detail" class="empty-state">
        <div class="empty-mark" aria-hidden="true">&gt;_</div>
        <h2>Select an agent</h2>
        <p>Inspect output, send a follow-up, or resolve blocked work.</p>
      </div>
      <div id="agent-detail" hidden>
        <div class="section-head detail-head">
          <div>
            <h2 id="detail-name"></h2>
            <p id="detail-meta"></p>
          </div>
          <span id="detail-status" class="status-pill"></span>
        </div>
        <p id="detail-task" class="task-text"></p>
        <div id="attention" class="attention" hidden></div>
        <div class="action-bar">
          <button id="stop" type="button" class="secondary">Stop</button>
          <button id="respawn" type="button" class="secondary">Respawn</button>
          <button id="remove" type="button" class="danger">Remove</button>
        </div>
        <form id="message-form" class="command-row">
          <input id="message" maxlength="8000" placeholder="Send a follow-up message" required>
          <button type="submit">Send</button>
        </form>
        <div class="output-head">
          <h3>Recent output</h3>
          <button id="refresh-logs" class="icon-button" title="Refresh output" aria-label="Refresh output">&#8635;</button>
        </div>
        <pre id="logs">Select refresh to load output.</pre>
      </div>
    </section>
  </main>
  <div id="toast" role="status" aria-live="polite"></div>
  <script src="/app.js" defer></script>
</body>
</html>
"""


REMOTE_CONTROL_CSS = """:root {
  color-scheme: light dark;
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  background: #f4f6f8;
  color: #17202a;
  letter-spacing: 0;
}
* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; background: #f4f6f8; }
button, input { font: inherit; letter-spacing: 0; }
button { cursor: pointer; }
header {
  min-height: 72px; padding: 14px 22px; display: flex; align-items: center; gap: 12px;
  background: #17202a; color: #f8fafc; border-bottom: 3px solid #18a572;
}
.brand-mark {
  width: 42px; height: 42px; display: grid; place-items: center; flex: 0 0 42px;
  background: #18a572; color: #071d16; font-weight: 800; border-radius: 6px;
}
h1, h2, h3, p { margin: 0; }
h1 { font-size: 18px; font-weight: 700; }
header p { color: #b7c0ca; font-size: 13px; margin-top: 3px; overflow-wrap: anywhere; }
header .status-pill { margin-left: auto; }
main { display: grid; grid-template-columns: minmax(320px, 42%) minmax(0, 1fr); min-height: calc(100vh - 72px); }
.roster, .detail { padding: 20px; min-width: 0; }
.roster { background: #ffffff; border-right: 1px solid #d8dee5; }
.detail { background: #f4f6f8; }
.section-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.section-head h2 { font-size: 17px; }
.section-head p, .detail-head p { color: #687481; font-size: 12px; margin-top: 4px; }
.icon-button {
  width: 36px; height: 36px; padding: 0; border: 1px solid #c9d1da; border-radius: 5px;
  background: #ffffff; color: #263442; font-size: 21px;
}
.command-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; margin-bottom: 16px; }
input {
  width: 100%; min-height: 40px; border: 1px solid #b9c3ce; border-radius: 5px;
  background: #ffffff; color: #17202a; padding: 9px 11px; outline: none;
}
input:focus { border-color: #0b7d58; box-shadow: 0 0 0 3px rgba(24, 165, 114, .14); }
button:not(.icon-button) {
  min-height: 40px; border: 1px solid #0b7d58; border-radius: 5px;
  background: #0b7d58; color: #ffffff; padding: 8px 14px; font-weight: 650;
}
button.secondary { background: #ffffff; color: #263442; border-color: #b9c3ce; }
button.danger { background: #ffffff; color: #b42318; border-color: #e2aaa5; }
.agent-list { display: grid; gap: 6px; }
.agent-row {
  width: 100%; min-height: 70px; display: grid; grid-template-columns: 10px minmax(0, 1fr) auto;
  align-items: center; gap: 10px; padding: 10px 12px; text-align: left;
  border: 1px solid #d8dee5; border-radius: 6px; background: #ffffff; color: #17202a;
}
.agent-row:hover, .agent-row.selected { border-color: #18a572; background: #f0faf6; }
.agent-row .dot { width: 9px; height: 9px; border-radius: 50%; background: #8794a1; }
.agent-row .dot.running { background: #168a61; }
.agent-row .dot.needs-input { background: #d97706; }
.agent-row .dot.failed, .agent-row .dot.lost { background: #c7352c; }
.agent-main { min-width: 0; }
.agent-name { font-size: 14px; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.agent-task { color: #687481; font-size: 12px; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.agent-state { color: #52606d; font-size: 11px; text-transform: uppercase; }
.status-pill {
  display: inline-flex; align-items: center; min-height: 26px; padding: 4px 9px;
  border: 1px solid #6f7c89; border-radius: 999px; font-size: 11px; font-weight: 700;
  background: #263442; color: #f8fafc;
}
.task-text { padding: 11px 0 16px; color: #354352; overflow-wrap: anywhere; }
.attention { border-left: 4px solid #d97706; background: #fff7e6; color: #482d07; padding: 14px; margin-bottom: 16px; }
.attention h3 { font-size: 14px; margin-bottom: 7px; }
.attention p { font-size: 13px; margin: 5px 0; overflow-wrap: anywhere; }
.attention .command-row { margin: 12px 0 0; }
.action-bar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.output-head { display: flex; align-items: center; justify-content: space-between; margin: 18px 0 8px; }
.output-head h3 { font-size: 14px; }
pre {
  min-height: 260px; max-height: calc(100vh - 410px); overflow: auto; margin: 0;
  border: 1px solid #c8d0d8; border-radius: 5px; background: #111820; color: #d6e0e8;
  padding: 13px; font: 12px/1.55 ui-monospace, SFMono-Regular, Consolas, monospace;
  white-space: pre-wrap; overflow-wrap: anywhere;
}
.empty-state { min-height: 60vh; display: grid; place-content: center; justify-items: center; text-align: center; color: #687481; }
.empty-mark { color: #0b7d58; font: 700 34px ui-monospace, monospace; margin-bottom: 12px; }
.empty-state h2 { color: #263442; font-size: 17px; margin-bottom: 5px; }
#toast {
  position: fixed; right: 18px; bottom: 18px; max-width: min(420px, calc(100vw - 36px));
  background: #17202a; color: #ffffff; padding: 11px 14px; border-radius: 5px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, .22); opacity: 0; pointer-events: none;
  transform: translateY(8px); transition: opacity .15s, transform .15s;
}
#toast.visible { opacity: 1; transform: translateY(0); }
@media (max-width: 760px) {
  header { padding: 12px 14px; }
  h1 { font-size: 15px; }
  main { grid-template-columns: 1fr; }
  .roster { border-right: 0; border-bottom: 1px solid #d8dee5; }
  .roster, .detail { padding: 14px; }
  pre { max-height: 420px; }
}
@media (prefers-color-scheme: dark) {
  :root, body, .detail { background: #10161d; color: #e5ebf0; }
  .roster { background: #161e27; border-color: #34404b; }
  .section-head p, .detail-head p, .agent-task, .agent-state, .task-text { color: #a8b3bd; }
  .icon-button, input, .agent-row, button.secondary, button.danger { background: #19232d; color: #e5ebf0; border-color: #465462; }
  .agent-row:hover, .agent-row.selected { background: #18352c; }
  .empty-state h2 { color: #e5ebf0; }
  .attention { background: #3a2b12; color: #ffe3ad; }
}
"""


REMOTE_CONTROL_JS = """'use strict';
const token = new URLSearchParams(location.hash.slice(1)).get('token') || '';
let state = { agents: [] };
let selectedId = null;
let toastTimer = null;

const byId = (id) => document.getElementById(id);
const api = async (path, options = {}) => {
  const response = await fetch(path, {
    ...options,
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json', ...(options.headers || {}) },
    cache: 'no-store'
  });
  const payload = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
};
const showToast = (message) => {
  const node = byId('toast');
  node.textContent = message;
  node.classList.add('visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => node.classList.remove('visible'), 2800);
};
const text = (tag, className, value) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = value;
  return node;
};
const current = () => state.agents.find((agent) => agent.id === selectedId) || null;

function renderRoster() {
  const project = state.projectRoot || 'Unknown project';
  byId('project').textContent = state.remoteControlName ? `${state.remoteControlName} · ${project}` : project;
  byId('summary').textContent = `${state.agents.length} agent${state.agents.length === 1 ? '' : 's'}`;
  const list = byId('agents');
  list.replaceChildren();
  for (const agent of state.agents) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = `agent-row${agent.id === selectedId ? ' selected' : ''}`;
    row.addEventListener('click', () => { selectedId = agent.id; renderRoster(); renderDetail(); loadLogs(); });
    row.append(text('span', `dot ${agent.status}`, ''));
    const main = text('span', 'agent-main', '');
    main.append(text('span', 'agent-name', agent.sessionName || agent.id));
    main.append(text('span', 'agent-task', agent.task || 'No task summary'));
    row.append(main, text('span', 'agent-state', agent.pending ? `${agent.status} +${agent.pending}` : agent.status));
    list.append(row);
  }
}

function attentionForm(agent) {
  const box = byId('attention');
  box.replaceChildren();
  box.hidden = true;
  if (agent.approval) {
    box.hidden = false;
    box.append(text('h3', '', `Approval: ${agent.approval.actionType}`));
    box.append(text('p', '', agent.approval.target));
    box.append(text('p', '', agent.approval.risk));
    const actions = text('div', 'action-bar', '');
    for (const [label, approved, scope] of [['Approve once', true, 'once'], ['Approve session', true, 'session'], ['Deny', false, 'once']]) {
      const button = text('button', approved ? '' : 'danger', label);
      button.type = 'button';
      button.addEventListener('click', () => mutate(`/api/agents/${agent.id}/approval`, {
        approved,
        scope,
        requestId: agent.approval.requestId,
      }));
      actions.append(button);
    }
    box.append(actions);
  } else if (agent.question) {
    box.hidden = false;
    box.append(text('h3', '', agent.question.header || 'Question'));
    box.append(text('p', '', agent.question.question));
    agent.question.options.forEach((option, index) => {
      const descriptions = agent.question.optionDescriptions || {};
      const description = descriptions[option];
      box.append(text('p', '', `${index + 1}. ${option}${description ? ` - ${description}` : ''}`));
    });
    const form = text('form', 'command-row', '');
    const input = document.createElement('input');
    input.maxLength = 8000;
    input.placeholder = agent.question.multiSelect ? 'Answer, e.g. 1,3' : 'Answer or option number';
    input.required = true;
    const button = text('button', '', 'Answer');
    button.type = 'submit';
    form.append(input, button);
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      mutate(`/api/agents/${agent.id}/answer`, {
        answer: input.value,
        requestId: agent.question.requestId,
      });
    });
    box.append(form);
  }
}

function renderDetail() {
  const agent = current();
  byId('empty-detail').hidden = Boolean(agent);
  byId('agent-detail').hidden = !agent;
  if (!agent) return;
  byId('detail-name').textContent = agent.sessionName || agent.id;
  byId('detail-meta').textContent = `${agent.id} | started ${agent.startedAt}`;
  byId('detail-status').textContent = agent.status;
  byId('detail-task').textContent = agent.task || 'No task summary';
  attentionForm(agent);
}

async function refresh() {
  try {
    state = await api('/api/state');
    if (selectedId && !state.agents.some((agent) => agent.id === selectedId)) selectedId = null;
    if (!selectedId && state.agents.length) selectedId = state.agents[0].id;
    byId('connection').textContent = 'Connected';
    renderRoster();
    renderDetail();
  } catch (error) {
    byId('connection').textContent = token ? 'Disconnected' : 'Token missing';
    showToast(error.message);
  }
}
async function loadLogs() {
  if (!selectedId) return;
  try {
    const payload = await api(`/api/agents/${selectedId}/logs`);
    byId('logs').textContent = [payload.stdout, payload.stderr ? `[stderr]\\n${payload.stderr}` : ''].filter(Boolean).join('\\n') || '(empty)';
  } catch (error) { showToast(error.message); }
}
async function mutate(path, body = {}) {
  try {
    const payload = await api(path, { method: 'POST', body: JSON.stringify(body) });
    showToast(payload.message || 'Done');
    await refresh();
    await loadLogs();
    return true;
  } catch (error) {
    showToast(error.message);
    return false;
  }
}

byId('refresh').addEventListener('click', refresh);
byId('refresh-logs').addEventListener('click', loadLogs);
byId('dispatch-form').addEventListener('submit', async (event) => { event.preventDefault(); const input = byId('dispatch-task'); if (await mutate('/api/agents', { task: input.value })) input.value = ''; });
byId('message-form').addEventListener('submit', async (event) => { event.preventDefault(); const input = byId('message'); if (await mutate(`/api/agents/${selectedId}/messages`, { message: input.value })) input.value = ''; });
byId('stop').addEventListener('click', () => mutate(`/api/agents/${selectedId}/stop`));
byId('respawn').addEventListener('click', () => mutate(`/api/agents/${selectedId}/respawn`));
byId('remove').addEventListener('click', () => { if (confirm('Remove this agent and its logs?')) mutate(`/api/agents/${selectedId}/remove`); });
refresh().then(loadLogs);
setInterval(refresh, 1200);
"""


__all__ = ["REMOTE_CONTROL_CSS", "REMOTE_CONTROL_HTML", "REMOTE_CONTROL_JS"]
