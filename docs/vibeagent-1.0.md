# VibeAgent 1.0 Acceptance Plan

VibeAgent 1.0 is scoped to a usable local coding agent, not full Claude Code
parity. A 1.0 run should reliably inspect an unfamiliar repository, edit files
inside the workspace, run relevant checks, repair failures, review safety, commit
local changes when asked, and resume from recorded session context.

## Acceptance Gates

| Gate | Capability | Required runtime evidence |
| --- | --- | --- |
| VA1-READ | Inspect repository state before editing | `project_overview`, `repo_map`, `read_file`, `read_file_context`, `search`, and `project_instructions` can gather bounded project context without approval. |
| VA1-EDIT | Make workspace-scoped code changes safely | `check_write_file`, `write_file`, `check_edit_file`, `edit_file`, `multi_edit_file`, and related file tools reject protected paths and require approval for mutation. |
| VA1-RUN | Run checks and surface failures | `command_check`, `check_run_commands`, `run_command`, `run_commands`, `focused_test_commands`, and `run_suggested_checks` can preflight and execute bounded project commands. |
| VA1-REPAIR | Iterate after failing checks | The agent loop can observe failed command output, edit again, rerun checks, and keep task steps accurate. |
| VA1-REVIEW | Block premature completion after changes | `final_review`, completion blockers, and suggested verification checks prevent finishing until changed-file review and relevant checks are complete. |
| VA1-COMMIT | Commit verified local work when requested | `check_git_stage`, `git_stage`, `check_git_commit`, and `git_commit` can stage explicit paths and create a local commit after approval. |
| VA1-RESUME | Recover useful session context | `session_summary`, `session_verification`, `run_session_verification`, `session_handoff`, `--resume`, and `--compact` preserve enough context to continue work. |
| VA1-SAFETY | Enforce workspace and command safety | Workspace path guards, protected files, approval policy, project permissions, hooks, sandbox support, and hard command blocks prevent unsafe side effects. |

## Current Evidence

- `tests.test_agent.AgentTests.test_run_agent_repairs_a_failing_script_and_finishes`
  covers write -> failed command -> repair -> successful command.
- `tests.test_agent.AgentTests.test_run_agent_continues_after_pending_suggested_check_is_run`
  covers final-review blockers for pending verification.
- `tests.test_agent.AgentTests.test_run_agent_keeps_verification_after_stage_and_commit`
  covers plan -> edit -> test -> stage -> commit -> final review.
- `tests.test_agent.AgentTests.test_run_agent_uses_existing_session_verification_on_resume`
  covers resume-time verification reuse.
- `tests.test_project_permissions`, `tests.test_workspace`, and
  `tests.test_command_sandbox` cover the main workspace and safety boundaries.

## 1.0 Exit Criteria

- The full unit suite passes from a clean worktree.
- A dedicated 1.0 acceptance test confirms every gate above maps to concrete
  tools and regression tests.
- At least one deterministic dogfood scenario exercises read, edit, run, repair,
  review, and commit behavior without real provider calls.
- `README.md` points contributors to this 1.0 acceptance plan.
