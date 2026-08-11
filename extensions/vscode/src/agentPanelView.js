'use strict';

function getAgentPanelHtml(nonce) {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}';">
  <title>VibeAgent Agents</title>
  <style nonce="${nonce}">
    * { box-sizing: border-box; }
    body { margin: 0; color: var(--vscode-foreground); background: var(--vscode-editor-background); font: 13px var(--vscode-font-family); }
    button, input, textarea { color: inherit; font: inherit; }
    button { min-height: 28px; border: 1px solid var(--vscode-button-border, transparent); color: var(--vscode-button-foreground); background: var(--vscode-button-background); cursor: pointer; }
    button:hover { background: var(--vscode-button-hoverBackground); }
    button.secondary { color: var(--vscode-foreground); background: var(--vscode-button-secondaryBackground); }
    button.danger { color: var(--vscode-errorForeground); background: transparent; border-color: var(--vscode-errorForeground); }
    input, textarea { width: 100%; border: 1px solid var(--vscode-input-border, transparent); background: var(--vscode-input-background); padding: 7px 8px; outline: none; }
    input:focus, textarea:focus { border-color: var(--vscode-focusBorder); }
    textarea { min-height: 72px; resize: vertical; }
    .shell { display: grid; grid-template-rows: 42px minmax(0, 1fr); height: 100vh; }
    header { display: flex; align-items: center; gap: 10px; padding: 0 12px; border-bottom: 1px solid var(--vscode-panel-border); }
    header strong { flex: 1; font-size: 13px; }
    #notice { overflow: hidden; color: var(--vscode-descriptionForeground); text-overflow: ellipsis; white-space: nowrap; }
    .layout { display: grid; grid-template-columns: minmax(190px, 27%) minmax(0, 1fr); min-height: 0; }
    aside { overflow: auto; border-right: 1px solid var(--vscode-panel-border); }
    .dispatch { padding: 10px; border-bottom: 1px solid var(--vscode-panel-border); }
    .row { display: flex; gap: 6px; margin-top: 7px; }
    .row button { flex: 0 0 auto; padding: 0 11px; }
    #agents { display: grid; }
    .agent { display: grid; grid-template-columns: 9px minmax(0, 1fr); gap: 8px; padding: 9px 10px; border: 0; border-bottom: 1px solid var(--vscode-panel-border); text-align: left; color: var(--vscode-foreground); background: transparent; }
    .agent.selected { background: var(--vscode-list-activeSelectionBackground); color: var(--vscode-list-activeSelectionForeground); }
    .dot { width: 8px; height: 8px; margin-top: 4px; border-radius: 50%; background: var(--vscode-descriptionForeground); }
    .dot.running { background: var(--vscode-testing-iconPassed); }
    .dot.needs-input { background: var(--vscode-editorWarning-foreground); }
    .dot.failed, .dot.approval-error, .dot.input-error { background: var(--vscode-errorForeground); }
    .agent strong, .agent span { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .agent span { margin-top: 3px; color: var(--vscode-descriptionForeground); font-size: 12px; }
    main { min-width: 0; overflow: auto; padding: 14px; }
    .meta { color: var(--vscode-descriptionForeground); }
    .status { display: inline-block; margin-left: 8px; color: var(--vscode-badge-foreground); background: var(--vscode-badge-background); padding: 2px 6px; }
    section { margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--vscode-panel-border); }
    section h2 { margin: 0 0 8px; font-size: 13px; }
    .attention { border-left: 3px solid var(--vscode-editorWarning-foreground); padding-left: 10px; }
    .actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 9px; }
    .actions button { padding: 0 10px; }
    pre { min-height: 120px; max-height: 38vh; overflow: auto; margin: 0; padding: 9px; border: 1px solid var(--vscode-panel-border); background: var(--vscode-textCodeBlock-background); white-space: pre-wrap; word-break: break-word; }
    .stderr { color: var(--vscode-errorForeground); }
    [hidden] { display: none !important; }
    @media (max-width: 620px) { .layout { grid-template-columns: 1fr; grid-template-rows: auto minmax(0, 1fr); } aside { max-height: 42vh; border-right: 0; border-bottom: 1px solid var(--vscode-panel-border); } }
  </style>
</head>
<body>
  <div class="shell">
    <header><strong>VibeAgent Agents</strong><span id="notice">Starting local control service...</span><button id="refresh" class="secondary" title="Refresh agents">Refresh</button></header>
    <div class="layout">
      <aside>
        <form id="dispatch" class="dispatch"><textarea id="task" maxlength="8000" required placeholder="Task for a new background agent"></textarea><div class="row"><button type="submit">Start agent</button></div></form>
        <div id="agents"></div>
      </aside>
      <main>
        <p id="empty" class="meta">No background agent selected.</p>
        <div id="detail" hidden>
          <h1 id="name" style="font-size:16px;margin:0 0 5px"></h1>
          <div><span id="identity" class="meta"></span><span id="status" class="status"></span></div>
          <p id="task-detail"></p>
          <div id="attention" class="attention" hidden></div>
          <section><h2>Follow-up</h2><form id="message" class="row"><input id="message-text" maxlength="8000" required placeholder="Message this agent"><button type="submit">Send</button></form></section>
          <section><h2>Process</h2><div class="actions"><button id="stop" class="secondary">Stop</button><button id="respawn" class="secondary">Respawn</button><button id="remove" class="danger">Remove</button></div></section>
          <section><h2>Output</h2><pre id="stdout"></pre><pre id="stderr" class="stderr" hidden></pre></section>
        </div>
      </main>
    </div>
  </div>
  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    let state = { projectRoot: '', agents: [] };
    let selectedId = null;
    const byId = (id) => document.getElementById(id);
    const send = (type, extra = {}) => vscode.postMessage({ type, ...extra });
    const element = (tag, className, value) => { const item = document.createElement(tag); item.className = className; item.textContent = value; return item; };
    function selected() { return state.agents.find((agent) => agent.id === selectedId) || null; }
    function render() {
      if (selectedId && !selected()) selectedId = null;
      if (!selectedId && state.agents.length) selectedId = state.agents[0].id;
      const list = byId('agents'); list.replaceChildren();
      for (const agent of state.agents) {
        const row = element('button', 'agent' + (agent.id === selectedId ? ' selected' : ''), ''); row.type = 'button';
        row.addEventListener('click', () => { selectedId = agent.id; send('select', { agentId: agent.id }); render(); });
        row.append(element('span', 'dot ' + agent.status, ''), element('span', '', ''));
        row.lastChild.append(element('strong', '', agent.sessionName || agent.id), element('span', '', (agent.task || 'No task') + ' | ' + agent.status));
        list.append(row);
      }
      const agent = selected(); byId('empty').hidden = Boolean(agent); byId('detail').hidden = !agent;
      if (!agent) return;
      byId('name').textContent = agent.sessionName || agent.id;
      byId('identity').textContent = agent.id + ' | started ' + agent.startedAt;
      byId('status').textContent = agent.pending ? agent.status + ' +' + agent.pending : agent.status;
      byId('task-detail').textContent = agent.task || 'No task summary';
      renderAttention(agent);
    }
    function actionButton(label, handler, className = '') { const button = element('button', className, label); button.type = 'button'; button.addEventListener('click', handler); return button; }
    function renderAttention(agent) {
      const box = byId('attention'); box.replaceChildren(); box.hidden = true;
      if (agent.approval) {
        box.hidden = false; box.append(element('h2', '', 'Approval: ' + agent.approval.actionType), element('p', '', agent.approval.target), element('p', 'meta', agent.approval.risk));
        const actions = element('div', 'actions', '');
        actions.append(
          actionButton('Approve once', () => send('approval', { agentId: agent.id, requestId: agent.approval.requestId, approved: true, scope: 'once' })),
          actionButton('Approve session', () => send('approval', { agentId: agent.id, requestId: agent.approval.requestId, approved: true, scope: 'session' })),
          actionButton('Deny', () => send('approval', { agentId: agent.id, requestId: agent.approval.requestId, approved: false, scope: 'once' }), 'danger')
        ); box.append(actions); return;
      }
      if (agent.question) {
        box.hidden = false; box.append(element('h2', '', agent.question.header || 'Question'), element('p', '', agent.question.question));
        const descriptions = agent.question.optionDescriptions || {};
        agent.question.options.forEach((option, index) => box.append(element('p', 'meta', (index + 1) + '. ' + option + (descriptions[option] ? ' - ' + descriptions[option] : ''))));
        const form = element('form', 'row', ''); const input = document.createElement('input'); input.required = true; input.maxLength = 8000; input.placeholder = 'Answer or option number';
        const button = element('button', '', 'Answer'); button.type = 'submit'; form.append(input, button);
        form.addEventListener('submit', (event) => { event.preventDefault(); send('answer', { agentId: agent.id, requestId: agent.question.requestId, answer: input.value }); }); box.append(form);
      }
    }
    byId('refresh').addEventListener('click', () => send('refresh'));
    byId('dispatch').addEventListener('submit', (event) => { event.preventDefault(); send('dispatch', { task: byId('task').value }); byId('task').value = ''; });
    byId('message').addEventListener('submit', (event) => { event.preventDefault(); const agent = selected(); if (agent) send('message', { agentId: agent.id, message: byId('message-text').value }); byId('message-text').value = ''; });
    for (const type of ['stop', 'respawn']) byId(type).addEventListener('click', () => { const agent = selected(); if (agent) send(type, { agentId: agent.id }); });
    byId('remove').addEventListener('click', () => { const agent = selected(); if (agent && confirm('Remove this agent and its logs?')) send('remove', { agentId: agent.id }); });
    window.addEventListener('message', (event) => {
      const message = event.data || {};
      if (message.type === 'state') { state = message.state; byId('notice').textContent = state.agents.length + ' agent' + (state.agents.length === 1 ? '' : 's'); render(); }
      if (message.type === 'logs' && message.agentId === selectedId) { byId('stdout').textContent = message.stdout || ''; byId('stderr').textContent = message.stderr || ''; byId('stderr').hidden = !message.stderr; }
      if (message.type === 'notice') byId('notice').textContent = message.message;
      if (message.type === 'error') byId('notice').textContent = 'Error: ' + message.message;
    });
    send('refresh');
  </script>
</body>
</html>`;
}

module.exports = { getAgentPanelHtml };
