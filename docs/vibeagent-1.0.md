# VibeAgent 1.0 Acceptance Plan

VibeAgent 1.0 is scoped to a usable local coding agent, not full Claude Code
parity. A 1.0 run should reliably inspect an unfamiliar repository, edit files
inside the workspace, run relevant checks, repair failures, review safety, commit
local changes when asked, and resume from recorded session context.

## Acceptance Gates

| Gate | Capability | Required runtime evidence |
| --- | --- | --- |
| VA1-TOOLS | Restrict model-visible and executable tools | Bare `--tools` remains a provider-free catalog command; `--tools "Read,Edit"` on a one-shot coding task expands compatible aliases, intersects main and subagent profiles, filters initial, deferred, and `ToolSearch` results, rejects hidden calls at runtime, and records the effective ceiling. Unconditional deny/`--disallowedTools` rules remove complete compatible alias families from the main agent, every subagent path, MCP server/wildcard results, and tool search; scoped path, command, domain, or agent rules remain available for action-level permission matching. `AskUserQuestion` accepts one to four structured questions with described options and single- or multi-select terminal answers while retaining the legacy one-question parser. MCP resources are discovered through bounded pagination and read only by exact advertised URI, with redacted bounded text and hidden binary blobs. `--tools ""` disables all tools and `--tools default` restores the default catalog. |
| VA1-BUDGET | Bound unattended provider spending | `-p --max-budget-usd` shares one provider-neutral cost gate across the main agent, profiles, subagents, goal evaluation, and structured output; terminal budget errors do not retry or execute an over-budget response, and missing usage or rates fail closed. |
| VA1-RELIABILITY | Continue through primary-model overload | `-p --fallback-model` switches only on typed 503/529 or explicit overload evidence, then keeps the fallback model across the main agent, profiles, subagents, retries, goal evaluation, and structured output while preserving audit events and budget accounting. |
| VA1-OUTPUT | Return validated machine-readable results | `-p --json-schema` runs the normal coding workflow first, then validates one provider-neutral Draft-07 JSON value without tools, retries invalid output up to three times, and exposes the result in JSON or stream-JSON output. |
| VA1-READ | Inspect repository state before editing | `project_overview`, `repo_map`, `read_file`, `read_file_context`, `search`, and `project_instructions` can gather bounded project context without approval. |
| VA1-EDIT | Make workspace-scoped code changes safely | `check_write_file`, `write_file`, `check_edit_file`, `edit_file`, `multi_edit_file`, and related file tools reject protected paths and require approval for mutation. |
| VA1-RUN | Run checks and surface failures | `command_check`, `check_run_commands`, `run_command`, `run_commands`, `focused_test_commands`, and `run_suggested_checks` can preflight and execute bounded project commands; interactive `!` shell mode reuses the same bounded executor and carries redacted output into resume context. |
| VA1-REPAIR | Iterate after failing checks | The agent loop can observe failed command output, edit again, rerun checks, and keep task steps accurate. |
| VA1-REVIEW | Block premature completion after changes | `final_review`, completion blockers, and suggested verification checks prevent finishing until changed-file review and relevant checks are complete. |
| VA1-COMMIT | Commit verified local work when requested | `check_git_stage`, `git_stage`, `check_git_commit`, and `git_commit` can stage explicit paths and create a local commit after approval. |
| VA1-RESUME | Recover useful session context | `session_summary`, `session_verification`, `run_session_verification`, and `session_handoff` preserve bounded evidence; explicit `--resume`, `--session-id`, and `/resume` append to the same session ID with its redacted non-system model/tool conversation, while branches/forks use a new ID and `--compact` or `/compact` deliberately start a new session from compressed handoff context. A nonblocking per-turn lease rejects concurrent writers to one session. |
| VA1-GOAL | Continue until an independently checked condition is met | `/goal` persists one bounded condition, runs evaluator-guided coding turns without changing approvals, and restores active goals only on explicit resume. |
| VA1-PEER | Coordinate independent local coding sessions | `ListAgents` discovers live same-machine sessions, `SendMessage` delivers bounded untrusted text over a user-only Unix socket, and running or idle receivers process messages without changing permission boundaries. |
| VA1-DELEGATE | Split bounded investigation into a subagent | `delegate_task`, `Task`, and `Agent` can run isolated read-only investigations synchronously or in the background; `TaskOutput` collects results, `TaskStop` requests cancellation, and completion remains blocked while a result is running or unread. `--agents` accepts a bounded JSON object of invocation-scoped profiles and shares safe structured validation with file profiles for prompt, mode, model, effort, tools, skills, memory, turns, isolation, permissions, scoped hooks/MCP, initial prompts, forced background execution, and display color. Dynamic definitions take precedence for that invocation and propagate through interactive, main, nested, background, workflow, and worktree paths without writing profile files or exposing executable definitions in catalogs. |
| VA1-WORKFLOW | Orchestrate resumable multi-agent fan-out | `/workflows run` executes a permission-restricted JavaScript workflow with `agent()` and bounded `pipeline()`, persists source and completed calls, and supports list, show, stop, and cache-backed resume. |
| VA1-PLUGIN | Load and distribute reusable extension bundles without bypassing safety | `/plugin` validates, installs, lists, details, enables, disables, and atomically uninstalls project-local plugins; local and public-HTTPS GitHub/Git/JSON marketplaces add, list, inspect, refresh, remove, and install relative or remote `plugin@marketplace` sources; enabled namespaced skills, commands, agents, hooks, and MCP servers flow through their existing parsers, approvals, network checks, and path guards. |
| VA1-PLAN | Produce a concrete read-only implementation plan | Plan mode exposes only read-only tools such as `project_overview`, `read_file`, and `tool_search`, denies hidden write attempts, and leaves the workspace unchanged. |
| VA1-SAFETY | Enforce workspace and command safety | Workspace path guards, protected files, approval policy, project permissions, hooks, sandbox support, and hard command blocks prevent unsafe side effects. Claude-compatible `dontAsk` keeps read-only tools available, executes only trusted explicit allow rules, disables approval prompts and sandbox auto-approval for other side effects, and records machine-readable denial decisions without request events. |

## Current Evidence

- `tests.test_mcp.McpRuntimeTests.test_agent_discovers_lists_and_reads_mcp_resource`
  runs `ToolSearch`, `ListMcpResourcesTool`, and `ReadMcpResourceTool` through
  the real Agent loop and stdio protocol, including approval requests and
  progressive activation of the resource reader.
- `tests.test_user_input.UserInputTests.test_agent_answers_structured_batch_and_exposes_machine_requests`
  covers a real two-question `AskUserQuestion` model call, described options,
  mixed single/multi-select answers, session events, one consolidated tool
  result, and per-question machine-output requests.
- `tests.test_agent_profile_extended_contract.AgentProfileExtendedContractTests`
  covers safe nested YAML, duplicate-key and field validation, catalog
  confidentiality, first-turn main-agent prompts, main and subagent permission
  modes, untrusted-project escalation refusal, forced plan mode, scoped command
  hooks, and real stdio MCP protocol calls for both main and delegated agents.
- `tests.test_dynamic_workflow_agent.DynamicWorkflowAgentTests.test_profile_can_force_workflow_agent_into_background_with_color`
  and `tests.test_background_delegate.BackgroundDelegateTests.test_background_agent_inherits_dynamic_profile`
  cover profile-forced background execution and color propagation through
  workflow, task collection, and background delegation.
- `tests.test_dynamic_agent_profiles.DynamicAgentProfileTests` and
  `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_delegate_with_dynamic_agent_before_repair_and_commit`
  cover bounded dynamic-profile parsing, shared profile validation, same-name
  CLI precedence, prompt confidentiality, delegated tool/mode enforcement, no
  profile-file persistence, and a complete investigation, repair, verification,
  review, and commit workflow through the real CLI.
- `tests.test_project_permissions.ProjectPermissionConfigTests.test_dont_ask_allows_trusted_cli_rules_and_denies_other_writes_without_prompting`,
  `tests.test_sandbox_auto_approval.SandboxAutoApprovalTests.test_noninteractive_policies_override_sandbox_auto_approval`,
  and `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_dont_ask_completes_preapproved_repair_without_prompting`
  prove default non-interactive denial, trusted CLI allow behavior, sandbox
  isolation, zero approval-request events, and a complete pre-approved repair,
  verification, and commit workflow.
- `tests.test_main_agent_profile.MainAgentProfileTests.test_cli_tool_ceiling_hides_and_blocks_unlisted_main_tools`,
  `tests.test_delegation.DelegationTests.test_code_subagent_inherits_cli_tool_ceiling`,
  and `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_tools_restriction_completes_repair_without_extra_tools`
  prove CLI parsing, alias expansion, profile intersection, schema filtering,
  runtime rejection, subagent inheritance, audit events, and a complete
  restricted repair, verification, and commit workflow.
- `tests.test_main_agent_profile.MainAgentProfileTests.test_unconditional_permission_deny_hides_alias_family_and_blocks_calls`,
  `tests.test_delegation.DelegationTests.test_code_subagent_inherits_unconditional_permission_denies`,
  `tests.test_agent_tool_registry.AgentToolRegistryTests.test_tool_search_does_not_rediscover_globally_denied_tools`,
  `tests.test_project_permissions.ProjectPermissionConfigTests.test_matches_mcp_server_and_wildcard_deny_rules`,
  and `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_stream_json_disallowed_tools_override_accept_edits`
  cover global deny visibility, runtime enforcement, alias families, all
  subagent entrypoints, tool-search filtering, MCP server wildcards, audit
  events, and deny precedence over `acceptEdits`.
- `tests.test_model_budget.ModelCostBudgetTests.test_parallel_calls_share_one_strict_gate`
  confirms concurrent model callers serialize through one shared budget and
  cannot all pass a stale pre-call check.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_budgeted_repair_verify_commit_and_report_cost`
  runs the complete deterministic repair, verification, and commit workflow
  through the real CLI under a USD budget and verifies auditable cost output.
- `tests.test_model_fallback.ModelFallbackTests.test_fallback_failure_retries_only_the_sticky_fallback`
  confirms an overloaded primary activates fallback once and later retries stay
  on the fallback model instead of repeatedly probing the primary.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_fallback_model_completes_repair_after_primary_overload`
  starts with a typed primary overload, then completes the full deterministic
  repair, verification, and local commit workflow through the fallback model.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_read_repair_verify_commit_and_finish`
  is the dedicated deterministic 1.0 dogfood scenario: project overview,
  file reads, failing test reproduction, fix, passing test rerun, local commit,
  final review, and recorded verification evidence without real provider calls.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_resume_after_interrupted_failure_and_commit`
  covers the same repair workflow split across two runs: the first run records a
  failing verification before interruption, `get_resume_context` reloads that
  evidence, and the resumed run fixes, verifies, and commits.
- `tests.test_session_conversation.SessionConversationTests`,
  `tests.test_cli_startup_context.CliStartupContextTests.test_resume_restores_persisted_conversation_but_compact_does_not`,
  and the resume coverage in `tests.test_cli_interactive_state` and
  `tests.test_cli_one_shot_code` cover atomic private conversation checkpoints,
  prompt/image/tool-payload redaction, corrupt-state fallback, same-ID explicit
  resume, fork isolation, and compact as a deliberate conversation boundary.
- `tests.test_session_turn_lock.SessionTurnLockTests` covers per-turn same-session
  writer exclusion, owner diagnostics, symlink refusal, and release after normal
  or exceptional turn exit.
- `tests.test_session_tasks.SessionTaskTests` covers Claude-compatible
  `TaskCreate`, `TaskGet`, `TaskList`, and `TaskUpdate`, including stable IDs,
  status updates, owners, acyclic dependencies, deletion cleanup, completion
  plan integration, session summaries, and task-graph inheritance on resume.
- `tests.test_scheduled_tasks.ScheduledTaskTests`,
  `tests.test_cron_expression.CronExpressionTests`, and
  `tests.test_cli_scheduled_tasks.CliScheduledTaskTests` cover Claude-compatible
  `CronCreate`, `CronList`, and `CronDelete`, local-time five-field parsing,
  deterministic jitter, one-shot and recurring delivery, seven-day expiry,
  resume filtering, symlink refusal, the disable flag, agent-turn delivery, and
  once-per-second interactive idle wakeups.
- `tests.test_goal_state.GoalStateTests`,
  `tests.test_goal_evaluator.GoalEvaluatorTests`, and
  `tests.test_cli_goal.CliGoalTests` cover strict atomic goal state, symlink
  refusal, bounded no-tool evaluation, immediate interactive execution, and
  one-shot continuation until independent acceptance.
- `tests.test_peer_messaging.PeerMessagingTests` and
  `tests.test_cli_peer_messaging.CliPeerMessagingTests` cover real Unix-socket
  registration and delivery, `SO_PEERCRED` sender validation, peer discovery,
  tool routing, accept/hold/refuse controls, held-message decisions, duplicate
  and queue bounds, active-turn injection, idle wakeups, and cleanup.
- `tests.test_dynamic_workflow_node.DynamicWorkflowNodeTests`,
  `tests.test_dynamic_workflow_runtime.DynamicWorkflowRuntimeTests`, and
  `tests.test_cli_dynamic_workflows.CliDynamicWorkflowTests` cover parallel
  ordered fan-out, the 16/1000 bounds, hidden host globals, disabled string code
  generation, cancellation, atomic state, session events, deterministic cached
  resume, path validation, command routing, and provider-free status listing.
- `tests.test_plugins.PluginManifestTests`, `tests.test_plugins.PluginRuntimeTests`,
  `tests.test_plugin_inline_components.PluginInlineComponentTests`,
  `tests.test_plugin_scope_settings.PluginScopeSettingsTests`,
  `tests.test_plugin_install_scopes.PluginInstallScopeTests`,
  `tests.test_plugin_marketplaces`, `tests.test_plugin_updates`, and
  `tests.test_cli_plugins.CliPluginTests`
  cover manifest and component
  validation, bounded non-symlink installation, atomic replacement and
  uninstall rollback, enable-state preservation, five-component namespaced
  discovery, file-backed and manifest-inline hook/MCP loading, plugin
  path-variable and sensitive user-configuration expansion, protected MCP cwd rejection,
  lifecycle commands, reload counts, provider-free management, atomic project/local
  `enabledPlugins` scopes and precedence, multi-scope cache retention and rollback, local marketplace
  validation and snapshot caching, qualified installation, refresh, cascade
  removal, version-one state compatibility, state-write rollback, explicit
  version-aware plugin updates, batch catalog refresh, per-marketplace automatic
  update settings, delayed background refresh, idle notifications, and global
  updater environment controls.
- `tests.test_main_agent_settings.PluginDefaultSettingsTests` and
  `tests.test_main_agent_settings.MainAgentSettingsTests` cover bounded
  non-symlink plugin settings, root-over-inline precedence, default-agent
  validation, CLI/project/plugin selection precedence, namespaced and unique
  bare plugin profiles, disabled defaults, conflict failure before provider
  access, and command-customized interactive subagent status rows.
- `tests.test_agent_profile_models.AgentProfileModelTests` and the provider
  client suites cover model/effort metadata, invalid values, main and subagent
  client scoping, `inherit`, parent-client isolation, Anthropic
  `output_config.effort`, model overrides for every built-in provider, and
  pre-request failure when a provider or custom client cannot apply effort.
- `tests.test_plugin_remote_sources`, `tests.test_plugin_ssh_sources`, and
  `tests.test_plugin_npm_sources` cover public credential-free HTTPS
  enforcement, HTTPS-only redirects, sanitized non-interactive HTTPS/SSH Git execution,
  public-host resolution, strict known-host checking, SSH config/proxy refusal,
  GitHub and direct-JSON marketplace refresh, `github`/`url`/`git-subdir`
  plugin sources, SHA/ref selection, npm registry metadata and archive integrity,
  script-free bounded npm extraction, runtime skill discovery, temporary-cache
  cleanup, and removal races that must not leave orphan plugins.
- `tests.test_plugin_user_config.PluginUserConfigTests` covers manifest
  `userConfig` types and constraints, project/local/environment precedence,
  required-value enable gates, local shared settings, mode-`0600` sensitive
  storage, redacted status, model-visible secret refusal, secure hook launch,
  and substitutions plus subprocess environments across skills, commands,
  agents, hooks, MCP, LSP, and monitors.
- `tests.test_user_runtime_settings.UserRuntimeSettingsTests` covers bounded
  user/project/local `env` precedence, explicit project trust, host environment
  priority, secret-safe validation, and propagation to provider configuration,
  commands, hooks, MCP servers, and LSP servers.
- `tests.test_user_mcp.UserMcpScopeTests` covers bounded non-symlink
  `~/.claude.json` loading, local/project/user precedence, cross-project stdio
  execution, `CLAUDE_PROJECT_DIR`, strict-source isolation, environment
  defaults and required values, and hard-block checks after command expansion.
- `tests.test_mcp_commands.McpCommandTests` and
  `tests.test_cli_mcp.CliMcpTests` cover provider-free `/mcp`
  list/get/add/add-json/remove flows, local/project/user writes, replacement,
  unrelated user-state and mode preservation, safe metadata output,
  pre-mutation validation, symlink refusal, and interactive dispatch.
- `tests.test_interactive_shell.InteractiveShellTests` and
  `tests.test_cli_shell_mode.CliShellModeTests` cover provider-free `!` command
  execution, hard command blocks, resumable command evidence, persisted-output
  redaction, same-session continuation, and session-directory/event-file
  symlink refusal before command execution.
- `tests.test_cli_completion.CliCompletionTests` and
  `tests.test_cli_idle_input.CliIdleInputTests` cover terminal-native fuzzy
  `@path` and slash-command Tab completion, ignored/sensitive/symlink filtering,
  scan and match bounds, readline restoration, non-TTY fallback, real input on
  the main thread, and idle callbacks that preserve scheduled and peer wakeups.
- `tests.test_prompt_file_mentions.PromptFileMentionTests` and
  `tests.test_agent_run_setup.AgentRunSetupTests` cover whole-file and exact
  `@path#5-10` / `@path#L5-L10` prompt references, canonical deduplication,
  numbered selected-line injection, malformed/reversed/oversized/out-of-file
  rejection, text-only selector enforcement, metadata-only persistence, and
  compaction retention.
- `tests.test_project_trust.ProjectTrustIntegrationTests` covers bounded and
  secret-redacted terminal previews before project permission allow rules are
  trusted; raw rules remain available only for permission matching.
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
  discovers the skill tools through Claude-compatible `ToolSearch`, loads one
  exact `.claude/skills/*/SKILL.md` through `Skill` with invocation arguments,
  follows the loaded instruction, then reads, edits, verifies, final-reviews,
  and commits.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_apply_claude_multi_edit_and_commit`
  applies a two-step Claude-compatible `MultiEdit`, including a `replace_all`
  edit entry, then reruns tests, commits, and verifies the recorded session.
- `tests.test_v1_dogfood.V1DogfoodTests.test_v1_agent_can_delegate_read_only_investigation_before_repair`
  delegates the first investigation through the Claude-compatible `Task` alias,
  lets the read-only subagent use `Read`, then the parent fixes, verifies, and
  commits the change.
- `tests.test_background_delegate.BackgroundDelegateTests` covers background
  task parsing, immediate start, non-blocking polling, blocking result
  collection, cooperative cancellation, completion blocking, and concurrent
  session-event writes.
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
- `tests.test_structured_output.StructuredOutputTests.test_reprompts_after_validation_error_and_records_valid_output`
  covers provider-neutral Draft-07 validation, bounded correction prompts,
  durable validation events, and usage accounting without tool calls.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_schema_repairs_then_returns_validated_output`
  runs the deterministic repair through the real CLI, verifies and commits the
  workspace change, then repairs an invalid structured result and returns the
  validated JSON value to the machine caller.
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
- CLI system-prompt replacement and append inputs accept inline text or bounded
  UTF-8 files for interactive and one-shot sessions. Replacement forms are
  mutually exclusive, append forms compose, relative file paths resolve from
  the invocation directory, and invalid files fail before a provider call.
- CLI `--add-dir` inputs grant interactive and one-shot coding sessions access
  to additional file roots across read, edit, search, code-intelligence,
  prompt-reference, and command-cwd workflows. Added roots remain isolated from
  project configuration, session storage, and dedicated Git tools; protected
  paths, symlink escapes, sandbox mounts, and worktree conflicts are enforced.
  Interactive `/add-dir` can list, add, remove, and clear roots; changes reach
  later agent turns, workflows, idle tasks, and absolute-path completion. The
  latest set is persisted as session state and restored by resume or compact,
  with missing stored paths ignored safely.
- `tests.test_session_branching.SessionBranchingTests`, interactive CLI state
  tests, and one-shot code tests cover named session branches, immutable source
  transcripts, task/cron/goal/directory inheritance, parent-context fallback
  before the first branch task, branch-local context afterward, first-turn
  workspace pinning, and malformed, cyclic, duplicate-name, or nonempty-target
  rejection.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_use_strict_mcp_config_before_repair_and_commit`
  runs the real CLI JSON path with `--mcp-config explicit.mcp.json
  --strict-mcp-config`, confirming an explicit MCP configuration can expose a
  Claude-style dynamic `mcp__server__tool` call before the agent repairs,
  verifies, reports, and commits.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_use_web_fetch_before_repair_and_commit`
  runs the real CLI JSON path through the Claude-compatible `WebFetch` alias,
  confirming fetched external evidence is fed into the next model turn before
  the agent repairs, verifies, reports, and commits.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_load_project_skill_before_repair_and_commit`
  runs the real CLI JSON path through Claude-compatible `ToolSearch` and
  `Skill`, confirming skill instructions are absent from the initial prompt,
  injected with invocation arguments only after the model requests the skill,
  then followed before repair, verification, review, and commit.
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
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_delegate_with_project_agent_profile_before_repair_and_commit`
  runs the real CLI JSON path through `Task` `subagent_type` with a
  `.claude/agents` profile, confirming profile instructions and tool limits are
  injected into the subagent prompt before the parent repairs, verifies, and
  commits.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_delegate_code_subagent_repair_and_commit`
  runs the real CLI JSON path through a code-mode `Task` subagent that reads,
  tests, edits, commits, reruns suggested checks, verifies the session, and
  returns a parent-auditable summary.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_create_and_check_checkpoint_before_commit`
  runs the real CLI JSON path through checkpoint creation, listing, status, and
  restore preflight before repair, verification, review, and commit, confirming
  a rollback point is available before workspace mutation.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_generates_ready_session_handoff_after_verified_commit`
  runs the real CLI JSON path through a verified commit and `session_handoff`,
  then reloads the persisted run's handoff report to confirm it is ready for
  continuation or compaction.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_plan_mode_inspects_without_mutating`
  runs the real CLI JSON path with `--approval plan`, confirming the plan-mode
  prompt and tool catalog expose read-only planning plus `ExitPlanMode` while
  hiding write, command, and commit tools and leaving the worktree unchanged.
- `tests.test_v1_cli_smoke.V1CliSmokeTests.test_v1_cli_json_can_resume_interrupted_run_and_commit`
  runs an interrupted deterministic repair dogfood through the real CLI
  `main()` JSON path, then resumes it through `--resume <runId>`, confirming
  same-ID continuation, prior-context loading, resume prompt injection, workspace repair,
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
  Claude-compatible file edit tools are approved by the `acceptEdits` permission source
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
- `tests.test_v1_live_dogfood.V1LiveDogfoodScriptTests.test_prepare_repo_creates_broken_calculator_and_command`
  covers the live-provider dogfood helper's throwaway repository setup and
  command generation, keeping the final manual gate reproducible.
- `tests.test_v1_live_dogfood.V1LiveDogfoodScriptTests.test_run_live_dogfood_feeds_ask_mode_approvals_and_reports_run_id`
  covers the helper's executable live path: it launches the ask-mode CLI, feeds
  bounded yes approvals through stdin, and reports the resulting session id for
  audit.
- `tests.test_v1_live_dogfood.V1LiveDogfoodScriptTests.test_audit_repo_fails_before_repair_and_passes_after_commit`
  covers the helper's local post-run audit logic without calling a provider,
  confirming the script rejects the initial broken repo and accepts a clean
  repaired commit.
- `tests.test_v1_live_dogfood.V1LiveDogfoodScriptTests.test_audit_session_events_requires_live_gate_evidence`
  covers the helper's session transcript gate, confirming a live dogfood cannot
  pass without ask-mode approval, read-before-write evidence, agent-run
  failing and passing verification, final review readiness, and completion
  readiness.
- `tests.test_v1_live_dogfood.V1LiveDogfoodScriptTests.test_audit_session_events_rejects_side_effect_before_approval`
  covers the transcript approval-order gate, confirming side-effect tool
  results cannot pass the live audit unless an approved decision appears first.
- `tests.test_v1_live_dogfood.V1LiveDogfoodScriptTests.test_audit_session_events_rejects_side_effect_path_outside_workspace`
  covers the live transcript workspace boundary gate, confirming side-effect
  file paths outside the throwaway repository block the live audit.
- `tests.test_v1_live_dogfood.V1LiveDogfoodScriptTests.test_audit_session_events_rejects_secret_leakage`
  covers the live transcript secret-safety gate, confirming high-confidence
  credential-like text blocks the live audit.
- `tests.test_v1_live_dogfood.V1LiveDogfoodScriptTests.test_audit_session_events_rejects_blocked_command_execution`
  covers the live transcript command-safety gate, confirming commands rejected
  by the project command safety rules block the live audit even if they appear
  in recorded session events.
- `tests.test_v1_live_dogfood.V1LiveDogfoodScriptTests.test_audit_session_events_accepts_complete_live_gate_evidence`
  covers the positive transcript audit path for a complete ask-mode run with
  inspection, approved edit and test actions, ready final review, and ready
  completion.
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
- `tests.test_instruction_context_compaction.InstructionContextCompactionTests`
  covers independent main/subagent path-instruction loading and rule reload
  after either context is compacted.
- `tests.test_delegation.DelegationTests` covers `SubagentStart` context
  injection for foreground and background workers plus `SubagentStop` blocking
  and retry for both text completion and the `finish` tool protocol.
- `tests.test_workspace_instruction_rules.WorkspaceInstructionRuleTests`
  covers recursive project-contained `@path` instruction imports, entrypoint
  deduplication, lazy owner claims, comment/code handling, and failure boundaries;
  `tests.test_agent_lifecycle_hooks.AgentLifecycleHookTests` covers include
  lifecycle events with their parent instruction file.
- `tests.test_project_permissions`, `tests.test_workspace`, and
  `tests.test_command_sandbox` cover the main workspace and safety boundaries.
- `tests.test_user_runtime_settings.UserRuntimeSettingsTests` covers
  cross-project user permissions, trusted user allow rules, user hooks with
  `CLAUDE_PROJECT_DIR`, source-aware sandbox exceptions and security floors,
  project deny precedence, and symlink refusal for user runtime settings.

## Verified 1.0 Exit Criteria

- Package metadata and runtime version report VibeAgent `1.0.0`.
- `npm run test:v1` passes from a clean worktree.
- `npm run test:v1:release` passes from a clean worktree, including compile
  checks, install smoke, and the full deterministic v1 gate.
- The full unit suite passes from a clean worktree.
- A dedicated 1.0 acceptance test confirms every gate above maps to concrete
  tools and regression tests.
- Deterministic dogfood scenarios exercise read, edit, run, repair, review,
  commit, and resume behavior without real provider calls.
- `README.md` points contributors to this 1.0 acceptance plan.
- [`docs/vibeagent-1.0-readiness.md`](vibeagent-1.0-readiness.md) documents
  the current release decision and the live-provider dogfood evidence for the
  1.0 release decision.
