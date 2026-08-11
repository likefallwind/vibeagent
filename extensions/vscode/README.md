# VibeAgent for VS Code

This extension launches the repository's VibeAgent CLI in a native VS Code
terminal, preserving terminal permission prompts while adding editor context.

## Commands

- `VibeAgent: Open Agent Panel` opens a workspace dashboard for dispatching and
  supervising background agents, viewing bounded logs, sending follow-ups,
  answering questions, and approving exact pending requests.
- `VibeAgent: Open Interactive Session` starts or reveals one interactive
  terminal for the active workspace.
- `VibeAgent: Ask About Selection` starts an approved one-shot coding task with
  the current file or selected line range as an `@path` reference.
- `VibeAgent: Insert File Reference` inserts that reference into an active
  VibeAgent terminal. If no session is open, it copies the reference instead.
- `VibeAgent: Send Current Diagnostics` starts a task with up to 20 bounded,
  explicitly untrusted diagnostics from the active file.
- `VibeAgent: Review Current File Changes` opens the VS Code diff viewer for
  the active file against Git `HEAD`.

Set `vibeagent.executable` and `vibeagent.arguments` when VibeAgent is installed
under a different Python interpreter or wrapper. The defaults run
`python -m vibeagent`.

Every terminal receives a private live-context file and random token through
its process environment. The extension refreshes only the active workspace file
path, selected line range, dirty flag, and up to 20 sanitized diagnostics. It
does not transmit selected source text or unsaved editor buffers. VibeAgent
revalidates this metadata on each turn and removes the two bridge variables from
project child-process environments.

The Agent Panel starts an authenticated Remote Control service bound to
`127.0.0.1`. Its random bearer token remains in the extension host and is never
sent to the Webview. Approval and question actions include the exact request ID
shown by the panel, so a stale click cannot answer a newer request.

Build `dist/vibeagent-vscode-1.0.0.vsix` from the repository root, then install
it through **Extensions: Install from VSIX...**:

```sh
python3 scripts/build_vscode_extension.py
```
