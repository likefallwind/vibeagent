# VibeAgent 1.0 Acceptance Plan

VibeAgent 1.0 is scoped to a usable local coding agent, not full Claude Code
parity. A 1.0 run should reliably inspect an unfamiliar repository, edit files
inside the workspace, run relevant checks, repair failures, review safety, commit
local changes when asked, and resume from recorded session context.

## Acceptance Gates

| Gate | Capability | Required runtime evidence |
| --- | --- | --- |
| VA1-TOOLS | Restrict model-visible and executable tools | Bare `--tools` remains a provider-free catalog command; `--tools "Read,Edit"` on a one-shot coding task expands compatible aliases, intersects main and subagent profiles, filters initial, deferred, and `ToolSearch` results, rejects hidden calls at runtime, and records the effective ceiling. Unconditional deny/`--disallowedTools` rules remove complete compatible alias families from the main agent, every subagent path, MCP server/wildcard results, and tool search; scoped path, command, domain, or agent rules remain available for action-level permission matching. `AskUserQuestion` accepts one to four structured questions with described options and single- or multi-select terminal answers while retaining the legacy one-question parser. MCP concrete resources and RFC 6570 URI templates are discovered through bounded pagination and read only by exact advertised URI or a matching template instance, with redacted bounded text and hidden binary blobs. `--tools ""` disables all tools and `--tools default` restores the default catalog. |
| VA1-BUDGET | Bound unattended provider spending | `-p --max-budget-usd` shares one provider-neutral cost gate across the main agent, profiles, subagents, prompt/agent Hook evaluation, goal evaluation, and structured output; terminal budget errors do not retry or execute an over-budget response, and missing usage or rates fail closed. |
| VA1-RELIABILITY | Continue through primary-model overload | `-p --fallback-model MODEL[,MODEL...]` switches only on typed 503/529 or explicit overload evidence, advances an ordered chain when a fallback is also overloaded, and then keeps the successful fallback across the main agent, profiles, subagents, prompt/agent Hook evaluation, retries, goal evaluation, and structured output while preserving per-model audit events and budget accounting. Interactive `/model <name>` atomically replaces the shared session client only after construction succeeds, preserves coding/chat conversation state, reaches later main, chat, and BTW calls, and `/model default` restores configured provider defaults without writing settings. `/effort` and `--effort` expose or set the current session level; supported Anthropic clients accept `low`, `medium`, `high`, `xhigh`, and `max`, `/effort auto` clears the override, model switches preserve it, `CLAUDE_CODE_EFFORT_LEVEL` has locked precedence over CLI and profiles, and unsupported or invalid changes fail before model requests without replacing the active client. `--autocompact auto|TOKENS` accepts Claude-compatible 100k-1m thresholds, propagates through main and delegated coding contexts, exposes the active value in `/status`, records estimated trigger evidence, and never prevents forced recovery from a provider context-limit error. |
| VA1-OUTPUT | Return responsive human output and validated machine-readable results | Interactive code and chat turns incrementally render provider text without exposing thinking or tool inputs, visibly separate retries and provider restarts, preserve non-streaming custom clients, and avoid duplicating the completed message. Coding turns with a merged `MessageDisplay` hook disable raw streaming and record the reason so final display transforms cannot be bypassed. `-p --json-schema` runs the normal coding workflow first, then validates one provider-neutral Draft-07 JSON value without tools, retries invalid output up to three times, and exposes the result in JSON or stream-JSON output. Optional stream-JSON user-message replay emits only normalized accepted user text with the run/session identity before agent events and filters system, assistant, event, result, and arbitrary input fields. |
| VA1-READ | Inspect repository state before editing | `project_overview`, `repo_map`, `read_file`, `read_file_context`, `search`, and `project_instructions` can gather bounded project context without approval. |
| VA1-EDIT | Make workspace-scoped code changes safely | `check_write_file`, `write_file`, `check_edit_file`, `edit_file`, `multi_edit_file`, and related file tools reject protected paths and require approval for mutation. |
| VA1-RUN | Run checks, exercise the application, and preserve a verified launch recipe | `command_check`, `check_run_commands`, `run_command`, `run_commands`, `focused_test_commands`, and `run_suggested_checks` can preflight and execute bounded project commands; interactive `!` shell mode reuses the same bounded executor and carries redacted output into resume context. `/verify` converts a requested behavior into observable CLI, process, port, HTTP, or browser criteria, distinguishes tests and reachability from real UI interaction, and cleans up only its own processes. `/run-skill-generator [app]` proves build, launch, readiness, drive, observation, and cleanup before writing a secret-free root or package-level `.claude/skills/run-<name>/SKILL.md`, reloads the result through bare or directory-qualified project skill discovery, and fails closed on ambiguous non-interactive app selection. Later verification prefers the most specific matching `verify` or `run-*` recipe. |
| VA1-BROWSER | Exercise and verify a real web UI | When the optional `agent-browser` executable is installed, deferred `browser_open`, `browser_snapshot`, `browser_act`, `browser_read`, `browser_screenshot`, and `browser_close` tools run one isolated browser session per VibeAgent session. Every call requires normal approval and is unavailable in Plan mode. The contract supports HTTP(S) navigation, accessibility references, bounded control interaction and DOM/console/error reads, atomic workspace screenshots, and cleanup while excluding arbitrary CLI arguments, JavaScript evaluation, profiles, credentials, cookies, uploads, proxy configuration, and network interception. VibeAgent uses a private empty config and scrubbed environment, locks navigation to the approved host, rejects URL credentials and unsafe or mixed-scope DNS answers, bounds output to 30,000 characters, and limits screenshots to 25 MiB inside non-protected non-symlink workspace paths. Missing optional runtime support returns a structured tool failure instead of crashing the agent. |
| VA1-IDE | Work from VS Code with editor-native context, session history, agent supervision, and review | The dependency-free extension under `extensions/vscode/` launches VibeAgent in real integrated terminals, preserving TTY approval behavior; it reuses a primary workspace session, opens parallel sessions, and resumes an exact recent local session selected from a bounded Quick Pick. A startup-activated status item displays the active workspace's open managed interactive-terminal count and starts or reveals a session while excluding one-shot task and verification terminals. A native Session Inspector loads one bounded provider-free aggregate with the persistent task graph, keeps workspace and session identity outside editable Markdown, and resumes the exact inspected ID. Its editor title exposes refresh, open-file, and continue-task actions plus resume and verification in overflow only while the extension's private URI registry recognizes the active document. Refresh Inspected Session re-reads that out-of-band ID and atomically updates the active Markdown snapshot, requiring modal confirmation before replacing local document edits and rejecting document races. Open Inspected File refreshes the report, filters candidates through lexical and real-workspace boundaries plus a 10 MiB regular-file limit, then revalidates the selected real path before opening it in the editor. Continue Inspected Task refreshes the exact graph, exposes only unblocked pending or in-progress entries, and launches the selected bounded untrusted task context in a visible one-shot terminal for that stored session. Running inspected verification refreshes that session, requires a modal confirmation, and launches at most 10 recorded checks in a visible one-shot terminal with exact argument-array flags. Provider-free history lookup invokes the machine-scoped executable with an argument array and no shell, bounds runtime/output/item count and rendered fields, rejects malformed, duplicate, control-bearing, or path-like IDs, passes only a validated ID to `--resume`, does not inherit bridge credentials, and reveals an already open resumed session instead of duplicating it. File references prefer the active managed terminal and otherwise use the primary session. The Agent Panel dispatches project-local background agents, refreshes status and bounded logs, sends follow-ups, answers structured questions, resolves approvals, reviews committed/staged/working/untracked changes in native base-to-current diffs, applies a confirmed exact reviewed snapshot from a terminal isolated agent into non-conflicting main-worktree paths as unstaged changes, explicitly opens an isolated worktree, and stops, respawns, or removes workers. Change review requires the private recorded session root to share the project's Git common directory and subdirectory scope; it returns at most 200 relative files, filters sensitive/generated paths, and rejects stale paths, symlinks, binary/non-UTF-8 content, and content over 1 MiB. Integration revalidates the snapshot under the agent transition lock, rejects active agents, truncated sets, stale snapshots, or any independently changed target before mutation, preserves unrelated main changes, supports bounded regular text/binary files, deletions, and executable bits, writes atomically, rolls back completed operations on failure, and never stages or commits. Absolute roots remain in the extension host, while bounded diff sides live only in an in-memory virtual-document provider. The panel starts Remote Control without a shell, accepts only an authenticated `127.0.0.1` URL, retains the bearer token in the extension host, exposes no token to the CSP-restricted Webview, validates its message allowlist and IDs, and submits the exact rendered request ID for every approval, answer, or integration. Explicit commands also run a selected-file task, insert a correctly quoted `@path#Lx-Ly` reference, send at most 20 bounded and explicitly untrusted diagnostics, and open the current file against Git `HEAD` in the native diff viewer. Every launched terminal and panel service receives an owner-only temporary live-context file authenticated by a random 256-bit token; active file, selection, dirty state, and sanitized diagnostics refresh atomically and are revalidated on every model turn. No source text or unsaved buffer is transmitted, and bridge credentials are stripped from project child-process environments. Executable settings are machine-scoped, launch arguments bypass shell interpolation, paths stay inside the active workspace or repository, and diagnostics cannot inject control characters or active `@file` references. `scripts/build_vscode_extension.py` creates a deterministic allowlisted VSIX accepted by an isolated VS Code Server installation. |
| VA1-REPAIR | Iterate after failing checks | The agent loop can observe failed command output, edit again, rerun checks, and keep task steps accurate. |
| VA1-REVIEW | Review changes deeply, simplify safely, and block premature completion | `deep_review` runs bounded parallel read-only profiles with root `REVIEW.md` guidance and independent evidence verification. Its defects profile covers correctness, security, and test risks; cleanup separates existing-helper reuse, simplicity, concrete efficiency, and abstraction placement; security separates access control, injection/execution, data exposure, and supply-chain/configuration risks and requires a verified attacker-to-impact path. Interactive and print-mode `/code-review` accept bounded local targets and effort levels, remain read-only by default, and permit edits only with explicit `--fix`; unsupported cloud/comment modes fail before a model request. `/simplify` runs all four cleanup reviewers, applies only justified behavior-preserving fixes, and requires focused checks plus `final_review`. `/security-review` strictly reads the current branch against cached `origin/HEAD`, assigns security severity, never fetches or edits, and fails on missing prerequisites. Completion blockers and suggested verification checks prevent finishing until changed-file review and relevant checks are complete. |
| VA1-COMMIT | Commit verified local work when requested | `check_git_stage`, `git_stage`, `check_git_commit`, and `git_commit` can stage explicit paths and create a local commit after approval. |
| VA1-RESUME | Recover useful session context | `session_summary`, `session_verification`, `run_session_verification`, and `session_handoff` preserve bounded evidence; explicit `--resume`, `--session-id`, and `/resume` append to the same session ID with its redacted non-system model/tool conversation, while branches/forks use a new ID and `--compact` or `/compact` deliberately start a new session from compressed handoff context. `-p --no-session-persistence` instead uses a private temporary session tree through final output, disables implicit prior-session loading, permits explicit source resume without mutation, and removes the non-resumable run on success or failure. `/btw` can inspect a bounded read-only rendering of the current mode's conversation through one tool-free provider call without changing in-memory or persisted history. `/recap` produces a one-line, tool-free status without mutating history; code and chat modes track automatic recap eligibility independently, and after three completed turns an idle three-minute callback uses a dedicated provider client with a bounded failure cooldown. A nonblocking per-turn lease rejects concurrent writers to one session. |
| VA1-BACKGROUND | Run, monitor, continue, and interactively attach to autonomous top-level coding sessions after the launcher exits | `--background` / `--bg` accepts a persistent one-shot task, writes a private short-lived launch payload, starts the normal CLI in a detached process group, and immediately returns a project-local agent ID. `agents` opens a dependency-free full-screen project dashboard that auto-refreshes sessions grouped by attention/working/stopped/completed state, preserves selection across refreshes, provides bounded stdout/stderr peek, dispatches new tasks with option-safe argument separation, queues replies, stops or respawns workers, confirms removal, and exits through an alternate-screen boundary before attaching. Dashboard dispatch adds a generated `--worktree` in Git projects so concurrent sessions cannot edit the same checkout; non-Git projects and ordinary shell background launches retain their explicit isolation behavior. Ask-mode side effects and structured `AskUserQuestion` calls publish owner-only exact-ID interactions, enter `needs-input`, and resume the original tool call after Agent View approves, denies, or validates a numbered, multi-select, or free-text answer; unresolved input remains a live worker state for send, stop, respawn, remove, and attach safety. CLI flags and interactive slash commands provide the same scriptable lifecycle operations. `attach ID` (also `--attach-background-agent ID`) claims a private process-bound foreground lease, waits for an active worker to finish its current turn at the serialized handoff boundary, then restores the exact transcript, launch configuration, invocation directory, and effective worktree through the full interactive CLI. Exiting or interruption releases the lease without deleting the supervisor or transcript; stale leases are recovered using PID start-time identity, `attaching`/`attached` states are observable, and conflicting lifecycle mutations are rejected. An atomic FIFO inbox and cross-platform transition lock serialize send, worker exit, and attach; immutable worker tokens prevent inherited internal environment from authorizing nested CLI processes. Durable exit markers, strict interaction parsing, owner-only storage, closed detached stdin, TTY validation, and explicit-key rejection keep execution bounded. Machine-global aggregation across unrelated project registries remains outside the 1.0 contract. |
| VA1-REMOTE | Control detached local sessions from a browser | `remote-control` serves a responsive project-scoped control plane for background agents with generated 256-bit bearer authentication, no-store/frame-denied/CSP responses, bounded JSON and text, status/log reads, dispatch and follow-up messages, exact-request-ID approval and structured-question responses, and stop/respawn/removal through the existing supervisor locks. Stale approval or answer submissions fail before writing a response. It binds loopback by default and requires a caller-supplied regular-file TLS certificate/key pair for non-loopback IPv4. This self-hosted mode does not claim claude.ai account integration, active foreground conversation synchronization, or cross-project aggregation. |
| VA1-GOAL | Continue until an independently checked condition is met | `/goal` persists one bounded condition, runs evaluator-guided coding turns without changing approvals, and restores active goals only on explicit resume. |
| VA1-PEER | Coordinate independent local coding sessions | `ListAgents` discovers live same-machine sessions, `SendMessage` delivers bounded untrusted text over a user-only Unix socket, and running or idle receivers process messages without changing permission boundaries. |
| VA1-DELEGATE | Split bounded investigation into a subagent | `delegate_task`, `Task`, and `Agent` can run isolated read-only investigations synchronously or in the background; `-p --append-subagent-system-prompt` adds one invocation-scoped constraint after profile and task-specific instructions for every direct, nested, and resumed subagent; `TaskOutput` collects results, `TaskStop` requests cancellation, and completion remains blocked while a result is running or unread. Experimental teams expose `TeamCreate` and `TeamDelete` only when enabled, persist one private team per session, reject cleanup while named teammates run, and retain compatible implicit creation for direct named `Agent` calls. `--agents` accepts a bounded JSON object of invocation-scoped profiles and shares safe structured validation with file profiles for prompt, mode, model, effort, tools, skills, memory, turns, isolation, permissions, scoped hooks/MCP, initial prompts, forced background execution, and display color. Dynamic definitions take precedence for that invocation and propagate through interactive, main, nested, background, workflow, and worktree paths without writing profile files or exposing executable definitions in catalogs. Git-backed CLI isolation, model `EnterWorktree`, and subagent isolation share one worktree creation primitive that processes repository-root `.worktreeinclude` rules through Git, copies only the intersection of explicitly included and already ignored untracked files, validates symlink, overwrite, runtime-path, repository-identity, file-count, and byte limits before copying, and removes partially initialized worktrees on failure. |
| VA1-MONITOR | React to background command or WebSocket events | `Monitor` uses Bash-equivalent approval for commands and a fresh explicit approval for each public WebSocket connection. Command stdout lines and individual WebSocket text, binary-placeholder, close-code, and exit events are delivered once as untrusted input during active turns or through idle interactive wakeups. WebSocket URLs reject credentials, private/link-local/metadata DNS results, malformed or duplicate subprotocols, and messages above 1 MiB. Both sources enforce bounded timeouts, support session-lifetime persistent mode, and stop through `TaskStop` or CLI session exit. |
| VA1-WORKFLOW | Orchestrate approved and resumable multi-agent fan-out | Interactive `/batch <instruction>` researches a large change, requires 5-30 independent non-overlapping work units, presents the full plan for explicit approval, then launches one background worktree-isolated code agent per unit and collects every commit, check, PR, or failure without mutating the parent checkout. Plan approval does not alter normal file, command, Git, network, push, or PR permissions. One-shot batch execution fails before a model request because it cannot approve or revise the plan. `/workflows run` executes a permission-restricted JavaScript workflow with `agent()` and bounded `pipeline()`, persists source and completed calls, and supports list, show, stop, and cache-backed resume. |
| VA1-PLUGIN | Load and distribute reusable extension bundles without bypassing safety | `/plugin` validates, installs, lists, details, enables, disables, and atomically uninstalls project-local plugins; local and public-HTTPS GitHub/Git/JSON marketplaces add, list, inspect, refresh, remove, and install relative or remote `plugin@marketplace` sources; enabled namespaced skills, commands, agents, hooks, and MCP servers flow through their existing parsers, approvals, network checks, and path guards. |
| VA1-PLAN | Produce and approve a concrete read-only implementation plan | `EnterPlanMode` switches a running agent to a read-only catalog; Plan mode denies hidden write attempts, and `ExitPlanMode` lets the user resume with per-action review, allow subsequent actions, or keep planning with feedback. The selected mode reaches later interactive turns, while profile-forced Plan mode cannot be exited by the model. |
| VA1-SAFETY | Enforce workspace and command safety | Workspace path guards, protected files, approval policy, project permissions, hooks, sandbox support, and hard command blocks prevent unsafe side effects. Claude-compatible `dontAsk` keeps read-only tools available, executes only trusted explicit allow rules, disables approval prompts and sandbox auto-approval for other side effects, and records machine-readable denial decisions without request events. Approved async command hooks retain the same command safety and sandbox boundary, cannot apply late permission decisions, separate user-only `systemMessage` from model `additionalContext`, wake idle interactive sessions only through `asyncRewake` exit code 2, and cancel at print/CLI teardown. Approved HTTP hooks POST at most 1 MiB of lifecycle input without environment proxies, use allowlisted header environment expansion, reject credential-bearing or cross-scope URLs and reserved transport headers, process 2xx plain/structured output through the normal decision path, and keep status, connection, input-limit, and timeout failures non-blocking. Approved MCP tool hooks apply bounded `${path}` input substitution, configured-server command safety, advertised-tool checks, normal MCP approval and transport limits, structured decision parsing, and non-blocking missing-server, protocol, or `isError` outcomes. Prompt hooks use bounded input expansion and strict no-tool `{ok, reason}` evaluation through the shared provider budget/fallback path. Experimental agent hooks use the same strict decision schema with at most 50 read-only inspection turns, no mutation, command, delegation, or user-input tools, and private Hook-specific audit events. `PermissionRequest` hooks run only immediately before ask-mode user approval; prompt and agent results are advisory, command/HTTP/MCP deny wins over allow, allow can replace input and apply bounded session or persisted rule, mode, and directory updates, updated actions are rechecked against project rules and workspace safety, and deny can interrupt the active turn. Failed or malformed updates fall back to the user. `PreCompact`/`PostCompact` wrap automatic and interactive manual compaction, while non-blocking `SessionEnd` receives one-shot and interactive exit reasons under a shared bounded timeout. Exhausted main-model API failures fire non-blocking `StopFailure` hooks with standard matcher categories and bounded redacted details; Hook output and failures never replace the original result. Default Pre/Post blocks halt the turn, `continueOnBlock` returns feedback, Stop/SubagentStop can continue work, and malformed or failed evaluations remain non-blocking. |

## Current Evidence

- `tests.test_background_agent_runtime.BackgroundAgentRuntimeTests`,
  `tests.test_background_agent_attachment.BackgroundAgentAttachmentTests`, and
  `tests.test_background_agent_followup.BackgroundAgentFollowupTests` plus
  `tests.test_cli_background_agents.BackgroundAgentCliTests` cover private
  launch payload consumption, detached argument construction, generated
  resumable names, PID-reuse protection, FIFO follow-ups, same-ID respawn,
  worktree-root continuation, worker-token isolation, process-bound foreground
  attachment, safe active-turn handoff, stale-lease recovery, failed-spawn rollback,
  durable completed/failed/stopped states, bounded logs, process-group stopping,
  transcript-preserving removal, local CLI routing, machine output, validation,
  full-screen grouped rendering, PTY-safe terminal restoration, dispatch/reply,
  lifecycle key actions, dashboard-to-attach switching, and interactive management.
- `tests.test_remote_control_server.RemoteControlServerTests` runs the real
  loopback HTTP server, proves exact bearer authentication and security headers,
  exercises state, bounded logs, dispatch, reply, exact-ID approval and question, stop,
  respawn, and removal routes, rejects non-TLS network binds, validates CLI
  routing, and syntax-checks the delivered browser JavaScript.
- `tests.test_browser_tools.BrowserToolContractTests` and
  `tests.test_browser_tools.BrowserRuntimeTests` prove parser/schema alignment,
  normal approval and Plan-mode boundaries, isolated session/config arguments,
  proxy/profile/secret environment scrubbing, approved-host persistence,
  link-local and mixed-scope DNS refusal, bounded output, structured missing-
  dependency errors, and atomic workspace-only screenshots. A release-stage
  smoke also drives a real local page through open, accessibility snapshot,
  fill, click, DOM read, console/error reads, screenshot, pixel inspection, and
  close.
- `tests.test_vscode_extension.VsCodeExtensionTests` plus the Node tests under
  `extensions/vscode/test/` prove the extension manifest, machine-only launch
  configuration, exact argument arrays, selected-line and quoted-path
  references, bounded diagnostic sanitization, bounded provider-free session
  discovery, exact-ID resume, bounded provider-free plan loading, editable
  plan-review documents with trusted out-of-band session metadata, exact-session
  inspector aggregation with fixed plan, verification, file, and timeline bounds,
  bounded persistent task graph serialization and validation with metadata omitted,
  deeply validated Markdown rendering, out-of-band identity, and exact-session
  inspector resume,
  refreshed verification confirmation, cancellation safety, and bounded exact-session
  verification launch in a visible terminal,
  reviewed-plan execution, structured session rewind point discovery, shared rewind
  preflight and execution reports, bounded checkpoint-patch review, trusted
  out-of-band rewind targets, repeated preflight, modal confirmation, exact new-
  session resume, parallel/primary terminal routing, command registration, native
  diff routing, token-isolated Agent Panel routing and lifecycle, exact request IDs,
  same-repository worktree validation, bounded in-memory base/current review,
  exact-snapshot integration routing, explicit worktree opening, deterministic
  VSIX contents, and JavaScript syntax. A release-
  stage install uses isolated `/tmp` user, server, and extension directories and
  confirms VS Code reports `vibeagent.vibeagent-vscode@1.0.0`.
- `tests.test_background_agent_integration.BackgroundAgentIntegrationTests`
  covers mixed committed/staged/working/binary/deleted/executable changes,
  unrelated-main preservation, exact-snapshot and terminal-state checks,
  all-path conflict preflight, idempotence, and injected-failure rollback.
- `tests.test_ide_context.IdeContextTests` proves the JavaScript-to-Python
  protocol, private-file and token checks, exact-workspace binding,
  sensitive/symlink refusal, selection and diagnostic bounds, prompt injection
  marking, secret redaction, and child-process environment stripping.
- `tests.test_mcp.McpRuntimeTests.test_agent_discovers_lists_and_reads_mcp_resource`
  runs `ToolSearch`, `ListMcpResourcesTool`, and `ReadMcpResourceTool` through
  the real Agent loop and stdio protocol, including approval requests and
  progressive activation of the resource reader, then instantiates and reads
  an advertised URI template.
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
- `tests.test_model_fallback.ModelFallbackTests.test_overloaded_fallback_advances_chain_and_stays_on_successful_model`
  confirms ordered fallback candidates advance only on their own overload,
  remain sticky after success, and report per-model uses and bounded transitions.
- `tests.test_cli_interactive_model.InteractiveModelTests` covers provider-specific
  override keys, bounded model-name validation, status and default reset, client
  replacement across coding turns, conversation preservation, and rollback to
  the prior client when replacement construction fails.
- `tests.test_cli_interactive_effort.InteractiveEffortTests` covers level
  validation, status without provider creation, application across coding
  turns, `auto` reset, model-switch inheritance, conversation preservation,
  and atomic rollback for unsupported providers.
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
- `tests.test_cli_no_session_persistence.CliNoSessionPersistenceTests` covers
  private temporary event storage, final JSON usage accounting, stream-json
  delivery before cleanup, cleanup on provider failure, persistent-goal refusal,
  and byte-for-byte source-session isolation during explicit resume.
- `tests.test_session_turn_lock.SessionTurnLockTests` covers per-turn same-session
  writer exclusion, owner diagnostics, symlink refusal, and release after normal
  or exceptional turn exit.
- `tests.test_btw.BtwTests` and `tests.test_cli_btw.CliBtwTests` cover bounded
  current-conversation rendering, binary omission, tool-free single responses,
  custom response preferences, invalid questions, interactive error recovery,
  and proof that side questions and answers do not enter a later coding turn.
- `tests.test_session_recap.SessionRecapTests` and
  `tests.test_cli_recap.InteractiveRecapTests` cover the three-turn/three-minute
  eligibility state machine, failure cooldown, environment opt-out, bounded
  tool-free summaries, manual history isolation, and dedicated-client idle
  recap delivery.
- `tests.test_session_tasks.SessionTaskTests` covers Claude-compatible
  `TaskCreate`, `TaskGet`, `TaskList`, and `TaskUpdate`, including stable IDs,
  status updates, owners, acyclic dependencies, deletion cleanup, completion
  plan integration, session summaries, and task-graph inheritance on resume.
- `tests.test_session_task_commands.SessionTaskCommandTests` proves the
  provider-free local CLI payload and exit codes, bounded redacted graph
  serialization, metadata omission, owner/dependency state, and fail-closed
  missing, malformed, oversized, and symlinked task stores.
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
  files, records the implementation plan, and verifies no edits, commands, or
  commits were attempted. `tests.test_plan_mode` separately verifies dynamic
  `EnterPlanMode`, approval-gated `ExitPlanMode`, keep-planning feedback,
  selected permission modes, forced-plan locking, and restored write approval.
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
  runs the same repair dogfood through the real CLI with matching stream-JSON
  input/output and `--replay-user-messages`, confirming normalized user input
  is acknowledged with matching run/session identity before agent events while
  system and assistant records remain context only, then the agent repairs,
  verifies, reports status, and commits.
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
- Interactive `/cd PATH` changes the main project while preserving the active
  conversation, mode, goal, approval policy, and valid additional roots. It
  closes old-project background resources, reloads target configuration, and
  records subsequent work in a new target-local session branch.
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
  confirming a read-only subagent receives the invocation-scoped appended
  system prompt, inspects project files, and returns a bounded summary before
  the parent agent repairs, verifies, reports, and commits. The prompt text is
  absent from session events.
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
- `tests.test_compact_session_end_hooks.CompactSessionEndHookRuntimeTests`
  covers automatic and interactive manual compaction inputs, bounded summaries,
  one-shot termination, interactive clear/exit/resume reasons, and SessionEnd
  timeout defaults.
- `tests.test_task_lifecycle_hooks.TaskLifecycleHookTests` covers matcher-free
  task Hook configuration, exact creation/completion input, rollback-safe
  blocking, `continue: false` turn halting, and the teammate coordination path.
- `tests.test_post_tool_batch_hooks.PostToolBatchHookTests` covers matcher-free
  parallel batches, provider-neutral result ID mapping, exact serialized
  responses, context injection, pre-request blocking, and subagent delivery.
- `tests.test_agent_teams.AgentTeamTests` covers matcher-free `TeammateIdle`
  configuration, text and `finish` continuation, exact team identity input,
  bounded provider-protocol-safe feedback, and explicit teammate stopping.
- `tests.test_worktree_lifecycle_hooks.WorktreeLifecycleHookTests` covers
  custom CLI/subagent worktree creation, non-Git cleanup, returned-path
  validation, and failure before delegated model execution.
- `tests.test_worktree_include.WorktreeIncludeTests`,
  `tests.test_cli_worktree.CliWorktreeTests`, and
  `tests.test_worktree_tools.WorktreeToolTests`, and
  `tests.test_subagent_worktree_isolation.SubagentWorktreeIsolationTests`
  cover Git-native include/ignore intersection and negation rules, pre-copy
  bounds, symlink and runtime-path refusal, CLI setup rollback, and ignored-file
  delivery into CLI, model-entered, and subagent worktrees.
- `tests.test_delegation.DelegationTests` covers `SubagentStart` context
  injection for foreground and background workers plus `SubagentStop` blocking
  and retry for both text completion and the `finish` tool protocol.
- `tests.test_workspace_instruction_rules.WorkspaceInstructionRuleTests`
  covers recursive project-contained `@path` instruction imports, entrypoint
  deduplication, lazy owner claims, comment/code handling, and failure boundaries;
  `tests.test_agent_lifecycle_hooks.AgentLifecycleHookTests` covers include
  lifecycle events with their parent instruction file, plus matcher-aware
  `UserPromptExpansion` field delivery, context injection, and blocking before
  the first main-model request.
- `tests.test_notification_hooks` covers supported handler configuration,
  permission and 60-second idle dispatch, exact lifecycle input, once-only idle
  delivery, user-only `systemMessage`, and non-blocking JSON or exit-code-2
  decisions.
- `tests.test_file_changed_hooks` covers literal matcher discovery, empty
  dynamic-only matchers, workspace and symlink boundaries, atomic watchPaths
  replacement, session-cwd relocation, add/change/unlink detection, active
  agent and interactive-idle polling, user-only output, non-blocking decisions,
  and persistent `CLAUDE_ENV_FILE` updates.
- `tests.test_message_display_hooks` covers matcher-free configuration, 10-second
  display and 30-second prompt-submit defaults, model-handler rejection, empty
  replacement, failed-hook fallback, exact complete-message input, UUID fields,
  user-only system messages, terminal rendering, explicit machine display fields,
  and isolation from canonical results and resumed model conversation.
- `tests.test_project_permissions`, `tests.test_workspace`, and
  `tests.test_command_sandbox` cover the main workspace and safety boundaries.
- `tests.test_user_runtime_settings.UserRuntimeSettingsTests` covers
  cross-project user permissions, trusted user allow rules, user hooks with
  `CLAUDE_PROJECT_DIR`, source-aware sandbox exceptions and security floors,
  project deny precedence, and symlink refusal for user runtime settings.
- `tests.test_deferred_tool_state.DeferredToolStateTests` covers print-mode
  `PreToolUse: defer`, private atomic pending-state persistence, exact tool ID
  replay on resume, completed batch-result preservation, unavailable-tool
  failure, machine output, and hook-supplied `AskUserQuestion` answers.
- `tests.test_async_hooks.AsyncHookRuntimeTests` covers approved non-blocking
  command hooks, ignored late permission decisions, private current-session
  state, user/model output separation, exactly-once next-turn context,
  exit-code-2 `asyncRewake`, print/CLI teardown cancellation, interactive idle
  wakeups, timeouts, and bounded session-timeline summaries.
- `tests.test_http_hooks.HttpHookConfigTests` and
  `tests.test_http_hooks.HttpHookIntegrationTests` cover bounded handler
  configuration, URL/header validation, explicit environment interpolation,
  real loopback JSON POST input, structured `PreToolUse` denial, lifecycle
  context delivery, proxy-independent scoped connections, request/response
  bounds, non-blocking failure behavior, and redacted session audit metadata.
- `tests.test_mcp_hooks.McpHookConfigTests` and
  `tests.test_mcp_hooks.McpHookIntegrationTests` cover bounded handler
  configuration, recursive typed payload substitution, missing-path refusal,
  real stdio MCP tool discovery and calls, structured `PreToolUse` denial,
  lifecycle context delivery, unavailable-server and `isError` non-blocking
  behavior, and ordinary MCP approval and audit paths.
- `tests.test_prompt_hooks.PromptHookConfigTests` and
  `tests.test_prompt_hooks.PromptHookIntegrationTests` cover supported-event
  and field validation, bounded `$ARGUMENTS` expansion and escaping, strict
  response parsing, scoped model/timeout overrides, default turn halting,
  `continueOnBlock` feedback, non-blocking evaluator errors, shared main-agent
  tool paths, and Stop/SubagentStop continuation.
- `tests.test_model_agent_hooks.AgentHookConfigTests` and
  `tests.test_model_agent_hooks.AgentHookIntegrationTests` cover supported-event and
  field validation, the 60-second default timeout, shared usage accounting,
  bounded multi-turn file inspection, strict text and `finish` decisions,
  absence of mutation, command, and delegation tools, default turn halting,
  `continueOnBlock` and Stop feedback, scoped model/timeout overrides, private
  Hook audit events, and non-blocking model or response failures.
- `tests.test_permission_request_hooks` covers strict allow/deny output parsing,
  five handler types, first-denial precedence, exact approval-boundary timing,
  project deny/ask priority, sandbox and noninteractive ceilings, failure
  fallback and audit, ordinary tool execution, and the shared special-tool path.

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
