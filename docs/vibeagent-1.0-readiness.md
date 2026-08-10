# VibeAgent 1.0 Readiness Audit

This audit records the automated readiness gate and the live-provider dogfood
evidence for calling VibeAgent 1.0 complete.

## Automated Gate

Run from a clean worktree:

```sh
npm run test:v1:release
```

The release suite also covers bounded coding-prompt `@path` references for
UTF-8 text and images, including workspace/sensitive-file rejection, metadata-
only event persistence, redacted conversation checkpoints that exclude prompt
attachments, one-turn image payload cleanup, and compaction-safe text context.
Text references support exact numbered `#5-10`, `#L5-L10`, and
single-line selectors with strict file and 1,000-line boundaries. Interactive
terminals add bounded Tab completion for safe project paths and slash commands
without opening a GUI; non-TTY input remains unchanged.
Permission rule text is redacted before it becomes model-visible
or enters session events, and terminal trust previews are redacted and limited
to 20 displayed rules while the original rule remains available for matching.
System prompts support replacement and append text or bounded UTF-8 file
inputs in both interactive and one-shot modes. Replacement text and file forms
are mutually exclusive, append sources compose deterministically, relative
paths use the invocation directory, and symbolic-link inputs are rejected.
Startup-level `--add-dir` grants bounded multi-root file, search, code-intel,
prompt-reference, and command-cwd access without treating added roots as
configuration, session, or Git roots. Every root keeps protected/sensitive-path
and symlink boundaries, overlapping roots use the most specific boundary, and
the command sandbox binds each explicitly granted root.
Interactive `/add-dir` can list, add, remove, or clear roots without restarting;
the active set is shared with agent turns, workflows, idle scheduled tasks, and
absolute-path completion. Directory changes are session events, and resume or
compact restores the latest valid set while ignoring unavailable stored paths.

That release gate expands to:

```sh
npm run build
npm run test:install
npm run test:v1:full
```

This gate must run:

- `python3 -m compileall -q vibeagent`
- `python3 scripts/install_smoke.py`
- `npm run test:v1`
- `python3 -m unittest discover -s tests -t . -q`

Passing this gate proves all package modules compile, the package installs from
outside the repository, both CLI entrypoints start, and the deterministic 1.0
acceptance suite, real CLI smoke paths, and full unit suite are internally
consistent.

## Automated Evidence

The automated suite currently covers these 1.0 surfaces:

- Install smoke: `scripts/install_smoke.py` creates a fresh virtual environment
  from outside the checkout, installs the package editable, and verifies both
  `python -m vibeagent --version` and `vibeagent --version`.
- Core ReAct loop: inspect, edit, run checks, repair, review, commit, finish.
- Claude-compatible tool aliases: `Read`, `Edit`, `MultiEdit`, `Write`,
  `NotebookRead`, `NotebookEdit`, `Bash`, `BashOutput`, `KillBash`,
  `TaskCreate`, `TaskGet`, `TaskList`, `TaskUpdate`, `TodoWrite`, `TodoRead`,
  `CronCreate`, `CronList`, `CronDelete`, `WebFetch`, `Task`, `TaskOutput`,
  `TaskStop`, `Agent`, and `ExitPlanMode`.
- Real CLI JSON and stream-json entrypoints, stdin input formats, resume,
  compact, permission overrides, `acceptEdits`, non-interactive `dontAsk`
  with trusted pre-approval and default denial, bounded invocation-scoped
  `--agents` definitions inherited by delegated runtimes, safe structured agent
  YAML, profile permission modes, scoped command hooks and stdio/HTTP MCP,
  initial prompts, forced background execution, task color, disallowed tools, one-shot
  `--tools` visibility and execution ceilings inherited by subagents, global
  deny alias-family removal across schemas, tool search, MCP wildcards, and
  every subagent path while scoped deny rules retain action-level matching,
  shared provider-cost budgets, sticky overload-model fallback, and
  pending-user-input output.
- Durable main-session conversation continuity: private atomic checkpoints at
  safe model/tool boundaries, fresh system/project context on every prompt,
  explicit resume and branch restoration, corrupt-state handoff fallback, and
  compact/clear/rewind boundaries that do not replay detailed history.
- Interactive `/branch [name]` and resumed `--fork-session`, including immutable
  source events, independent first-turn workspaces, state inheritance, named
  resume, branch discovery, bounded lineage fallback, and malformed/cyclic
  metadata rejection.
- Interactive and one-shot system-prompt text/file inputs, including bounded
  UTF-8 reads, deterministic structured-input merging, and machine-readable
  validation failures before provider creation.
- Interactive and one-shot additional working directories, including
  invocation-relative CLI resolution, model-visible absolute roots, core file
  and command execution, configuration isolation, sandbox mounts, and rejection
  of unlisted, protected, sensitive, symlink-escaping, or worktree-conflicting
  paths. Interactive add/remove/clear changes, external-root completion, session
  event persistence, and interactive, one-shot, resume, and compact restoration
  are covered directly.
- Provider-free interactive `!` shell mode with bounded execution, hard command
  blocks, redacted resumable output, and pre-execution session-path validation.
- User and project integrations: `~/.claude/settings.json`, trusted project and
  local settings environments, user/local MCP scopes in `~/.claude.json`,
  `.mcp.json`, provider-free scoped MCP management, strict MCP config,
  `.claude/skills`, `.claude/agents`, tool and session lifecycle hooks, project
  slash commands, checkpoints, session handoff, focused tests, code-mode
  subagents, and background read-only subagent lifecycle control.
- Experimental agent teams: approved named teammates, independent background
  contexts, stable session identities, shared task ownership and dependencies,
  peer and lead mailboxes, automatic lead delivery, and teardown cancellation.
- Session scheduling: standard local-time cron expressions, deterministic
  jitter, one-shot and recurring delivery, idle CLI wakeups, seven-day expiry,
  no-catch-up behavior, atomic persistence, and filtered resume restoration.
- Autonomous goals: one persisted completion condition, strict bounded no-tool
  evaluation after each coding turn, evaluator-guided continuation, interactive
  status and clearing, explicit resume restoration, and one-shot looping.
- Same-machine peer messaging: live Unix-socket discovery through `ListAgents`,
  plain-text `SendMessage` delivery, sender-process verification, bounded
  queues, accept/hold/refuse controls, held inbox decisions, active-turn
  injection, idle interactive wakeups, and permission-boundary preservation.
- Scoped instructions: nested instruction files and path rules load independently
  in main and subagent contexts and become eligible for reload after compaction.
- Safety boundaries: workspace path guards, approval policy, hard command
  blocks, final-review blockers, protected files, source-aware user/project
  permissions, environment propagation, hooks, and sandbox checks.

The source of truth for exact test names and gates is
[`docs/vibeagent-1.0.md`](vibeagent-1.0.md).

## Live Provider Gate

Before declaring 1.0 complete, run at least one live-provider dogfood against a
throwaway repository, not this fixture suite. The run must use the installed CLI
entrypoint and a real provider configuration.

Prepare the throwaway repository and print the command with:

```sh
python3 scripts/live_dogfood_v1.py --prepare --force --print-command
```

Minimum command shape printed by the script:

```sh
python3 -m vibeagent --cwd /tmp/vibeagent-live-dogfood --approval ask --max-iterations 20 "Inspect this repo with read-only tools, run `python -m unittest discover -s tests` to observe the failing test before editing, fix the failure, rerun unittest until it passes, review, commit, rerun any final suggested checks, and finish only when final_review is ready."
```

The live dogfood is passing only if all of these are true:

- The agent inspects repository state before editing.
- The agent asks for approval before side effects when `--approval ask` is used.
- The agent edits only files inside the target workspace.
- The agent runs the relevant failing and passing checks.
- `final_review` is ready before completion.
- The final git worktree is clean and contains one intentional local commit.
- `session_handoff` for the run is ready after completion.
- The run transcript has no secret leakage, unsafe command execution, or
  unapproved mutation.

After the live run completes, audit local outcomes with:

```sh
python3 scripts/live_dogfood_v1.py --audit --run-id <run-id>
```

To run and audit in one reproducible command, use:

```sh
python3 scripts/live_dogfood_v1.py --prepare --force --run --audit-after-run
```

The audit checks both repository state and session transcript evidence: ask-mode
approval policy, inspection before side effects, approval requests and approved
decisions, prior approval for side effects, workspace-bound side-effect paths,
transcript secret leakage, blocked command execution, agent-run failing and
passing unittest verification, ready final review, ready completion, and ready
session handoff.

## Current Decision

Status: `complete-for-v1-release`.

Release package version: `1.0.0`.

Reason: the automated 1.0 gate is broad and passing, the install smoke proves
the packaged CLI entrypoints from outside the checkout, and the live-provider
dogfood gate passed on a non-fixture throwaway repository.

Live provider evidence:

- Date: 2026-08-08
- Provider: MiniMax via `MINIMAX_API_KEY`
- Throwaway repo: `/tmp/vibeagent-live-dogfood`
- Session: `2026-08-08T02-51-11-792Z-db4de4e5`
- Command:
  `python3 scripts/live_dogfood_v1.py --prepare --force --run --audit-after-run --approval-count 30 --run-timeout-ms 600000`
- Audit result: all repository, approval, failing/passing unittest,
  `final_review`, completion, and handoff checks passed.
