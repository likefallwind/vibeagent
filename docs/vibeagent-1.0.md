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
| VA1-DELEGATE | Split bounded investigation into a subagent | `delegate_task`, `Task`, and `Agent` can run isolated read-only investigations whose summaries return to the parent agent before edits. |
| VA1-PLAN | Produce a concrete read-only implementation plan | Plan mode exposes only read-only tools such as `project_overview`, `read_file`, and `tool_search`, denies hidden write attempts, and leaves the workspace unchanged. |
| VA1-SAFETY | Enforce workspace and command safety | Workspace path guards, protected files, approval policy, project permissions, hooks, sandbox support, and hard command blocks prevent unsafe side effects. |

## Current Evidence

- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_read_repair_verify_commit_and_finish`
  is the dedicated deterministic 1.0 dogfood scenario: project overview,
  file reads, failing test reproduction, fix, passing test rerun, local commit,
  final review, and session verification recovery without real provider calls.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_resume_after_interrupted_failure_and_commit`
  covers the same repair workflow split across two runs: the first run records a
  failing verification before interruption, `get_resume_context` reloads that
  evidence, and the resumed run fixes, verifies, and commits.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_complete_repair_with_claude_code_tool_aliases`
  runs the repair workflow through Claude-compatible tool names and fields:
  `TodoWrite`, `LS`, `Glob`, `Grep`, `Read`, `Bash`, `Edit`, and `TodoRead`,
  then verifies and commits.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_create_new_file_with_claude_write_and_commit`
  creates a new helper source file through the Claude-compatible `Write` alias,
  edits existing code to call it, reruns tests, final-reviews, stages both
  files, commits, and verifies the recorded session.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_edit_notebook_with_claude_tools_and_commit`
  reads and edits a project notebook through Claude-compatible `NotebookRead`
  and `NotebookEdit`, reruns a regression test, final-reviews, commits, and
  verifies the recorded session.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_use_claude_mcp_tool_before_repair_and_commit`
  discovers a configured local MCP server through `mcp_tools`, calls its
  dynamic Claude-style `mcp__server__tool` alias for bounded external evidence,
  then fixes, tests, final-reviews, commits, and verifies the session.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_runs_project_hooks_around_claude_edit_and_commits`
  runs configured project `PreToolUse` and `PostToolUse` hooks around a
  Claude-compatible `Edit`, keeps hook output in local runtime state, then
  verifies, final-reviews, commits, and reruns session verification.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_manage_claude_background_process_before_repair`
  starts a Claude-style background `Bash`, inspects it through `BashOutput`,
  stops it through `KillBash`, then fixes, verifies, final-reviews, and commits.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_use_web_fetch_before_repair`
  fetches an external technical contract through the Claude-compatible
  `WebFetch` alias before reading, editing, testing, final-reviewing, and
  committing the local repair.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_reviews_git_diff_before_commit`
  verifies a commit path that explicitly reads `git_status` and a scoped
  `git_diff` after tests pass and before final review, staging, and commit.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_loads_project_instructions_and_repo_map_before_repair`
  explicitly loads project instruction files through `project_instructions` and
  a bounded repository map through `repo_map` before reading, editing, testing,
  final-reviewing, and committing.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_finds_and_runs_focused_tests_before_commit`
  finds related tests for a changed source file, turns them into focused test
  commands, runs those commands, then final-reviews and commits.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_creates_and_checks_checkpoint_before_commit`
  creates an explicit rollback checkpoint before editing, confirms checkpoint
  status and restore preflight after the edit, then verifies, final-reviews, and
  commits.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_generates_session_handoff_after_verified_commit`
  finishes a verified local commit, reruns recorded session verification, and
  then emits a structured `session_handoff` and confirms the completed run's
  handoff is ready for continuation or compaction.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_clarify_then_repair_verify_and_commit`
  uses the Claude-compatible `AskUserQuestion` alias to ask one blocking
  clarification, returns the selected answer to the model, then reads, edits,
  verifies, final-reviews, and commits.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_load_project_skill_then_repair_verify_and_commit`
  lists project skills, loads one exact `.claude/skills/*/SKILL.md` only on
  demand, follows the loaded skill instruction, then reads, edits, verifies,
  final-reviews, and commits.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_apply_claude_multi_edit_and_commit`
  applies a two-step Claude-compatible `MultiEdit`, including a `replace_all`
  edit entry, then reruns tests, commits, and verifies the recorded session.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_delegate_read_only_investigation_before_repair`
  delegates the first investigation through the Claude-compatible `Task` alias,
  lets the read-only subagent use `Read`, then the parent fixes, verifies, and
  commits the change.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_delegate_with_project_agent_profile_before_repair`
  delegates the first investigation to a `.claude/agents` project profile via
  `Task` `subagent_type`, injects the profile instruction into the subagent
  prompt, preserves the read-only allowlist, then lets the parent fix, verify,
  final-review, and commit.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_delegate_code_subagent_repair_and_commit`
  delegates the whole repair to a code-mode `Task` subagent, which reads,
  edits, runs tests, commits, reruns suggested checks, performs final review,
  and returns its summary for the parent to audit.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_plan_mode_inspects_without_mutating`
  runs a read-only planning pass that inspects the project, reads the target
  files, records the implementation plan through the Claude-compatible
  `ExitPlanMode` alias, and verifies no edits, commands, or commits were
  attempted.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_repair_verify_commit_and_report_ready`
  runs the deterministic repair dogfood through the real CLI `main()` one-shot
  JSON path, confirming argument parsing, provider creation, completion-ready
  machine output, workspace repair, verification, and local commit.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_input_format_can_repair_verify_commit_and_report_ready`
  runs the same repair dogfood through the real CLI `--input-format json -`
  stdin path, confirming structured automation input can supply the user task,
  system prompt, and assistant prior context before the agent repairs, verifies,
  reports JSON status, and commits.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_stream_json_input_format_can_repair_verify_commit_and_report_ready`
  runs the same repair dogfood through the real CLI `--input-format
  stream-json -` stdin path, confirming newline-delimited automation input can
  supply the same task, system prompt, and assistant prior context before the
  agent repairs, verifies, reports JSON status, and commits.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_use_strict_mcp_config_before_repair_and_commit`
  runs the real CLI JSON path with `--mcp-config explicit.mcp.json
  --strict-mcp-config`, confirming an explicit MCP configuration can expose a
  Claude-style dynamic `mcp__server__tool` call before the agent repairs,
  verifies, reports, and commits.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_use_web_fetch_before_repair_and_commit`
  runs the real CLI JSON path through the Claude-compatible `WebFetch` alias,
  confirming fetched external evidence is fed into the next model turn before
  the agent repairs, verifies, reports, and commits.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_runs_project_hooks_around_claude_edit_and_commits`
  runs the real CLI JSON path with configured project `PreToolUse` and
  `PostToolUse` hooks around a Claude-compatible `Edit`, confirming hooks fire
  before and after the edit before the agent verifies, reports, and commits.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_manage_background_process_before_repair_and_commit`
  runs the real CLI JSON path through Claude-compatible background `Bash`,
  `BashOutput`, and `KillBash` aliases, confirming a long-running process can
  be started, inspected, stopped, and kept out of the way before repair,
  verification, review, and commit.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_delegate_read_only_investigation_before_repair_and_commit`
  runs the real CLI JSON path through the Claude-compatible `Task` alias,
  confirming a read-only subagent can inspect project files and return a
  bounded summary before the parent agent repairs, verifies, reports, and
  commits.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_create_and_check_checkpoint_before_commit`
  runs the real CLI JSON path through checkpoint creation, listing, status, and
  restore preflight before repair, verification, review, and commit, confirming
  a rollback point is available before workspace mutation.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_generates_ready_session_handoff_after_verified_commit`
  runs the real CLI JSON path through a verified commit and `session_handoff`,
  then reloads the persisted run's handoff report to confirm it is ready for
  continuation or compaction.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_resume_interrupted_run_and_commit`
  runs an interrupted deterministic repair dogfood through the real CLI
  `main()` JSON path, then resumes it through `--resume <runId>`, confirming
  prior-context loading, resume prompt injection, workspace repair,
  verification, and local commit.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_compact_interrupted_run_and_commit`
  runs the same interrupted deterministic repair dogfood through the real CLI
  `main()` JSON path, then continues it through `--compact <runId>`, confirming
  explicit compact-context loading, prompt injection, workspace repair,
  verification, and local commit.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_stream_json_can_repair_with_allowed_tools_and_report_events`
  runs the deterministic repair dogfood through the real CLI `main()` one-shot
  `stream-json` path with per-run `--allowed-tools` overrides, confirming
  ordered event streaming, trusted permission source reporting,
  Claude-compatible `Bash` and `Edit` tool aliases, completion-ready machine
  output, workspace repair, verification, and local commit.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_stream_json_accept_edits_auto_allows_claude_edit`
  runs the same real CLI `stream-json` path with `--permission-mode
  acceptEdits` and without an explicit `Edit` allowed-tool override, confirming
  the Claude-compatible edit is approved by the `acceptEdits` permission source
  while other side-effecting tools still require explicit trusted rules.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_stream_json_accept_edits_auto_allows_claude_notebook_edit`
  runs a real CLI `stream-json` notebook repair with `--permission-mode
  acceptEdits` and without an explicit `NotebookEdit` allowed-tool override,
  confirming notebook cell edits are covered by the same Claude-compatible edit
  permission mode.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_stream_json_disallowed_tools_override_accept_edits`
  runs a real CLI `stream-json` path with both `--permission-mode acceptEdits`
  and `--disallowed-tools Edit`, confirming the per-run deny rule takes
  precedence over the automatic edit allow rule and leaves the workspace
  unchanged.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_dangerously_skip_permissions_can_repair_with_claude_aliases`
  runs the deterministic Claude-compatible repair dogfood through the real CLI
  `main()` one-shot JSON path with `--dangerously-skip-permissions`, confirming
  the automation shortcut can repair, verify, and commit without interactive
  approval prompts.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_reports_pending_user_input_for_machine_callers`
  runs a real CLI `main()` JSON path where the model uses the Claude-compatible
  `AskUserQuestion` alias and no interactive input handler is available,
  confirming machine callers receive `stopReason=user_input`,
  `pendingUserInput`, and structured `userInputRequests` while the workspace
  remains unchanged.
- `tests.test_project_prompt_commands.ProjectPromptCommandCliTests.test_one_shot_custom_command_expands_to_code_task_with_metadata`
  covers Claude-style project slash commands in one-shot code mode: a
  `.claude/commands/*.md` template expands before the agent run, while command
  provenance is recorded in task metadata.
- `tests.test_agent.AgentTests.test_run_agent_repairs_a_failing_script_and_finishes`
  covers write -> failed command -> repair -> successful command.
- `tests.test_agent.AgentTests.test_run_agent_continues_after_pending_suggested_check_is_run`
  covers final-review blockers for pending verification.
- `tests.test_agent.AgentTests.test_run_agent_keeps_verification_after_stage_and_commit`
  covers plan -> edit -> test -> stage -> commit -> final review.
- `tests.test_agent.AgentTests.test_run_agent_uses_existing_session_verification_on_resume`
  covers resume-time verification reuse.
- `tests.test_delegation.DelegationTests.test_parent_agent_receives_subagent_summary_as_tool_result`
  covers parent/subagent message flow and safe subagent lifecycle events.
- `tests.test_project_permissions`, `tests.test_workspace`, and
  `tests.test_command_sandbox` cover the main workspace and safety boundaries.

## 1.0 Exit Criteria

- `npm run test:v1` passes from a clean worktree.
- The full unit suite passes from a clean worktree.
- A dedicated 1.0 acceptance test confirms every gate above maps to concrete
  tools and regression tests.
- Deterministic dogfood scenarios exercise read, edit, run, repair, review,
  commit, and resume behavior without real provider calls.
- `README.md` points contributors to this 1.0 acceptance plan.
