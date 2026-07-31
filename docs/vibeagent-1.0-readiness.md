# VibeAgent 1.0 Readiness Audit

This audit records the automated readiness gate and the live-provider dogfood
evidence for calling VibeAgent 1.0 complete.

## Automated Gate

Run from a clean worktree:

```sh
npm run test:v1:release
```

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
- `python3 -m unittest discover -s tests -q`

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
  `TodoWrite`, `TodoRead`, `WebFetch`, `Task`, `Agent`, and `ExitPlanMode`.
- Real CLI JSON and stream-json entrypoints, stdin input formats, resume,
  compact, permission overrides, `acceptEdits`, disallowed tools, and
  pending-user-input output.
- Project integrations: `.mcp.json`, strict MCP config, `.claude/skills`,
  `.claude/agents`, project hooks, project slash commands, checkpoints,
  session handoff, focused tests, and code-mode subagents.
- Safety boundaries: workspace path guards, approval policy, hard command
  blocks, final-review blockers, protected files, and sandbox-related checks.

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
decisions, agent-run failing and passing unittest verification, ready final
review, ready completion, and ready session handoff.

## Current Decision

Status: `complete-for-v1-release`.

Release package version: `1.0.0`.

Reason: the automated 1.0 gate is broad and passing, the install smoke proves
the packaged CLI entrypoints from outside the checkout, and the live-provider
dogfood gate passed on a non-fixture throwaway repository.

Live provider evidence:

- Date: 2026-07-15
- Provider: MiniMax via `MINIMAX_API_KEY`
- Throwaway repo: `/tmp/vibeagent-live-dogfood`
- Session: `2026-07-15T01-46-18-965Z-7adb0ef6`
- Command:
  `python3 scripts/live_dogfood_v1.py --prepare --force --run --audit-after-run --approval-count 30 --run-timeout-ms 600000`
- Audit result: all repository, approval, failing/passing unittest,
  `final_review`, completion, and handoff checks passed.
