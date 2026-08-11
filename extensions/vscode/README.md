# VibeAgent for VS Code

This extension launches the repository's VibeAgent CLI in a native VS Code
terminal, preserving terminal permission prompts while adding editor context.

## Commands

- `VibeAgent: Open Agent Panel` opens a workspace dashboard for dispatching and
  supervising background agents, viewing bounded logs, sending follow-ups,
  answering questions, approving exact pending requests, and reviewing bounded
  worktree changes in VS Code's native diff viewer. For a stopped isolated
  agent, `Apply changes` confirms and applies the exact reviewed snapshot to
  non-conflicting main-worktree paths as unstaged changes. An explicit action
  opens the isolated worktree in a new VS Code window.
- `VibeAgent: Open Interactive Session` starts or reveals one interactive
  terminal for the active workspace.
- `VibeAgent: Open New Session` starts another independent interactive terminal
  for parallel work in the active workspace.
- `VibeAgent: Resume Session` reads the bounded provider-free local session
  catalog, lets you choose a recent entry, and resumes its exact ID. Selecting
  an ID already open in this VS Code window reveals that terminal.
- `VibeAgent: Inspect Session` selects a recent session and opens one bounded
  overview, plan, verification, file, and timeline report as native Markdown.
- `VibeAgent: Resume Inspected Session` resumes the exact session associated
  with the active inspector document.
- `VibeAgent: Refresh Inspected Session` reloads the exact session associated
  with the active inspector and updates that Markdown document in place.
- `VibeAgent: Continue Inspected Task` refreshes the exact inspected task graph,
  lets you choose an unblocked pending or in-progress task, and continues it in
  a visible one-shot terminal for the stored session.
- `VibeAgent: Run Inspected Verification` refreshes the active inspector,
  confirms its current failed and pending checks, and reruns up to 10 checks in
  a visible one-shot terminal for the exact stored session.
- `VibeAgent: Review Session Plan` selects a recent session, reads its structured
  local plan, and opens it as editable Markdown.
- `VibeAgent: Execute Reviewed Plan` resumes the exact session associated with
  the active plan document and runs the reviewed text as a bounded one-shot
  task. Session identity is retained outside the editable document.
- `VibeAgent: Review Session Rewind` selects an exact session checkpoint and
  `both`, `code`, or `conversation` mode, runs a provider-free preflight, and
  opens bounded staged and unstaged checkpoint patches as Markdown.
- `VibeAgent: Execute Reviewed Rewind` rechecks the active review, requires an
  explicit modal confirmation, and performs the stored operation. Conversation
  rewinds open the exact newly created branch session; edited review text cannot
  change the target identity or mode.
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

Session discovery runs the configured executable without a shell using
`--json --sessions`. It has a 10-second timeout, bounded stdout/stderr and item
counts, and validates every ID and display field before opening Quick Pick or
passing `--resume`. The discovery subprocess receives no live-context bridge
credentials. File references go to the active managed VibeAgent terminal, then
fall back to the primary workspace session.

Session inspection uses one provider-free, credential-isolated
`--json --session-inspect RUN_ID` request. The client validates identity,
status, counts, truncation flags, and every bounded field before opening the
document. At most 20 plan items, 50 persistent tasks, 50 checks per verification group, 100 files,
and 80 timeline events are accepted. Workspace, session, and display-name
metadata stay outside editable Markdown, so document edits cannot redirect the
resume command.

Inspector refresh uses the exact session metadata retained by the extension,
never edited Markdown identity. It replaces an unchanged generated snapshot in
place. Local document edits require a modal `Replace Inspector` confirmation;
cancellation is inert, and any active-document or text change while awaiting
confirmation aborts the replacement. Refresh output passes through the same
250,000-character rendering ceiling.
The same report contains up to 50 persistent `TaskCreate` graph entries. The
extension validates numeric IDs, unique shown tasks, status totals, owners,
dependency lists, blocked flags, and the 100-task store ceiling before rendering
the dedicated `Persistent Tasks` section. A corrupt graph rejects the whole
inspector instead of appearing empty.

Task continuation refreshes the exact inspected session immediately before
selection. It lists active work before pending work and excludes completed or
dependency-blocked entries. The selected bounded task fields are labeled as
untrusted context in the one-shot prompt; the exact validated session ID stays
out of band, cancellation is inert, and ordinary CLI approval rules still
apply.

Verification execution refreshes the inspector before displaying a modal
confirmation. Only an explicit `Run Checks` response opens a terminal with
`--run-session-verification`, the exact stored session ID, a 10-check limit,
and bounded source-context and diagnostic extraction. The argument array uses
no shell, and the one-shot terminal is excluded from file-reference routing.

Plan review uses the same provider-free, credential-isolated process boundary
with `--json --plan RUN_ID`. It validates bounded report and item fields before
opening an untitled editor. Reviewed-plan execution keeps `--resume RUN_ID`
ahead of the task argument and does not route file references into the one-shot
terminal.

Session rewind uses three provider-free structured CLI calls: checkpoint
discovery, shared preflight, and execution. Review additionally loads the exact
checkpoint diff, with bounded process output and patch sizes. The extension
keeps workspace, session, checkpoint, and mode metadata out of the editable
document, repeats preflight before execution, and shows a modal warning before
mutation. `code` restores the checkpoint worktree, `conversation` creates a new
branch without changing files, and `both` performs both operations.

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

Change metadata is limited to 200 project-relative files. The extension host
keeps the validated absolute worktree path private, fetches at most 1 MiB of
UTF-8 text per diff side through the authenticated API, and stores both sides
only in bounded in-memory virtual documents. The Webview receives neither file
contents nor absolute worktree paths.

The integration endpoint revalidates the 64-character snapshot ID while holding
the agent transition lock. It refuses active agents, truncated review sets,
stale snapshots, and any target path independently changed in the main
worktree. Regular text or binary files, deletions, and executable bits are
applied within bounded limits; partial failures roll back completed operations.
It does not stage or commit files.

Build `dist/vibeagent-vscode-1.0.0.vsix` from the repository root, then install
it through **Extensions: Install from VSIX...**:

```sh
python3 scripts/build_vscode_extension.py
```
