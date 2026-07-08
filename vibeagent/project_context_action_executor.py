from __future__ import annotations

from .process_runtime import execute_run_command_item
from .runtime_checks import build_command_check_observation
from .tool_catalog import get_tool_search_report
from .types import (
    AgentAction,
    CheckFocusedTestCommandsAction,
    CheckFocusedTestCommandsObservation,
    CheckSuggestedChecksAction,
    CheckSuggestedChecksObservation,
    CommandResult,
    FocusedTestCommand,
    FocusedTestCommandsAction,
    FocusedTestCommandsObservation,
    Observation,
    ProjectCommand,
    ProjectCommandsAction,
    ProjectCommandsObservation,
    ProjectInstructionSource,
    ProjectInstructionsAction,
    ProjectInstructionsObservation,
    ProjectManifest,
    ProjectManifestItem,
    ProjectManifestsAction,
    ProjectManifestsObservation,
    ProjectOverviewAction,
    ProjectOverviewObservation,
    ProjectTodo,
    ProjectTodosAction,
    ProjectTodosObservation,
    RelatedTestCandidate,
    RelatedTestsAction,
    RelatedTestsObservation,
    RunCommandItem,
    RunFocusedTestCommandsAction,
    RunFocusedTestCommandsObservation,
    RunSuggestedChecksAction,
    RunSuggestedChecksObservation,
    RuntimeToolInfo,
    SuggestedCheck,
    SuggestChecksAction,
    SuggestChecksObservation,
    ToolSearchAction,
    ToolSearchObservation,
)
from .workspace import (
    build_repo_map,
    find_related_tests,
    read_environment_info,
    read_git_info,
    read_project_commands,
    read_project_instruction_sources,
    read_project_manifests,
    read_project_todos,
    suggest_focused_test_commands,
    suggest_project_checks,
)


def execute_project_context_action(
    workspace,
    action: AgentAction,
    command_timeout_ms: int = 30_000,
) -> Observation | None:
    if isinstance(action, SuggestChecksAction):
        try:
            suggestions = suggest_project_checks(workspace, max_commands=action.max_commands)
            checks = [SuggestedCheck(**item) for item in suggestions["checks"]]
            return SuggestChecksObservation(
                kind="suggest_checks",
                ok=bool(suggestions["ok"]),
                checks=checks,
                total=int(suggestions["total"]),
                truncated=bool(suggestions["truncated"]),
                changed_files=list(suggestions["changed_files"]),
                message=str(suggestions["message"]),
            )
        except ValueError as error:
            return SuggestChecksObservation(
                kind="suggest_checks",
                ok=False,
                checks=[],
                total=0,
                truncated=False,
                changed_files=[],
                message=str(error),
            )

    if isinstance(action, CheckSuggestedChecksAction):
        try:
            suggestions = suggest_project_checks(workspace, max_commands=action.max_commands)
            suggested_checks = [SuggestedCheck(**item) for item in suggestions["checks"]]
            checks = [
                build_command_check_observation(workspace, item.command, item.cwd)
                for item in suggested_checks
            ]
            failed_count = sum(1 for check in checks if not check.ok)
            truncated = bool(suggestions["truncated"])
            ok = failed_count == 0 and not truncated
            status = "incomplete" if truncated else ("all available" if ok else "one or more failed")
            return CheckSuggestedChecksObservation(
                kind="check_suggested_checks",
                ok=ok,
                checks=checks,
                suggested_checks=suggested_checks,
                total=int(suggestions["total"]),
                truncated=truncated,
                max_commands=action.max_commands,
                message=f"Preflighted {len(checks)}/{int(suggestions['total'])} suggested check command(s); {failed_count} failed; {status}.",
            )
        except ValueError as error:
            return CheckSuggestedChecksObservation(
                kind="check_suggested_checks",
                ok=False,
                checks=[],
                suggested_checks=[],
                total=0,
                truncated=False,
                max_commands=action.max_commands,
                message=str(error),
            )

    if isinstance(action, RunSuggestedChecksAction):
        try:
            suggestions = suggest_project_checks(workspace, max_commands=action.max_commands)
            suggested_checks = [SuggestedCheck(**item) for item in suggestions["checks"]]
            runnable_checks = [item for item in suggested_checks if item.available]
            skipped_unavailable = len(suggested_checks) - len(runnable_checks)
            results: list[CommandResult] = []
            stopped_early = False
            for item in runnable_checks:
                result = execute_run_command_item(
                    workspace,
                    RunCommandItem(
                        command=item.command,
                        cwd=item.cwd,
                        timeout_ms=action.timeout_ms,
                        max_output_chars=action.max_output_chars,
                        extract_output_contexts=action.extract_output_contexts,
                        extract_output_diagnostics=action.extract_output_diagnostics,
                        context_lines=action.context_lines,
                        max_diagnostics=action.max_diagnostics,
                        max_contexts=action.max_contexts,
                        max_bytes_per_context=action.max_bytes_per_context,
                    ),
                    command_timeout_ms,
                )
                results.append(result)
                failed = result.exit_code != 0 or result.timed_out or result.exit_code is None
                if failed and action.stop_on_failure:
                    stopped_early = len(results) < len(runnable_checks)
                    break
            truncated = bool(suggestions["truncated"])
            ok = (
                not truncated
                and skipped_unavailable == 0
                and len(results) == len(runnable_checks)
                and all(result.exit_code == 0 and not result.timed_out for result in results)
            )
            status = "incomplete" if truncated else ("all passed" if ok else "one or more failed or were unavailable")
            return RunSuggestedChecksObservation(
                kind="run_suggested_checks",
                ok=ok,
                results=results,
                suggested_checks=suggested_checks,
                total=int(suggestions["total"]),
                truncated=truncated,
                max_commands=action.max_commands,
                stopped_early=stopped_early,
                skipped_unavailable=skipped_unavailable,
                message=(
                    f"Ran {len(results)}/{len(runnable_checks)} available suggested check command(s); "
                    f"{status}."
                ),
            )
        except ValueError as error:
            return RunSuggestedChecksObservation(
                kind="run_suggested_checks",
                ok=False,
                results=[],
                suggested_checks=[],
                total=0,
                truncated=False,
                max_commands=action.max_commands,
                stopped_early=False,
                skipped_unavailable=0,
                message=str(error),
            )

    if isinstance(action, ProjectCommandsAction):
        try:
            metadata = read_project_commands(
                workspace,
                max_commands=action.max_commands,
                max_files=action.max_files,
            )
            commands = [ProjectCommand(**item) for item in metadata["commands"]]
            return ProjectCommandsObservation(
                kind="project_commands",
                ok=bool(metadata["ok"]),
                commands=commands,
                total=int(metadata["total"]),
                truncated=bool(metadata["truncated"]),
                total_files=int(metadata["total_files"]),
                scanned_files=int(metadata["scanned_files"]),
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return ProjectCommandsObservation(
                kind="project_commands",
                ok=False,
                commands=[],
                total=0,
                truncated=False,
                total_files=0,
                scanned_files=0,
                message=str(error),
            )

    if isinstance(action, ToolSearchAction):
        try:
            metadata = get_tool_search_report(
                action.query,
                max_matches=action.max_matches,
                category=action.category,
                approval_required=action.approval_required,
            )
            return ToolSearchObservation(
                kind="tool_search",
                ok=bool(metadata["ok"]),
                query=str(metadata["query"]),
                matches=[item for item in metadata["matches"] if isinstance(item, dict)],
                total=int(metadata["total"]),
                shown=int(metadata["shown"]),
                truncated=bool(metadata["truncated"]),
                category=str(metadata["category"]) if metadata.get("category") is not None else None,
                approval_required=(
                    bool(metadata["approvalRequired"]) if metadata.get("approvalRequired") is not None else None
                ),
                suggestions=[str(item) for item in metadata.get("suggestions", [])],
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return ToolSearchObservation(
                kind="tool_search",
                ok=False,
                query=action.query,
                matches=[],
                total=0,
                shown=0,
                truncated=False,
                category=action.category,
                approval_required=action.approval_required,
                suggestions=[],
                message=str(error),
            )

    if isinstance(action, RelatedTestsAction):
        try:
            metadata = find_related_tests(
                workspace,
                paths=action.paths,
                max_paths=action.max_paths,
                max_candidates=action.max_candidates,
            )
            candidates = [RelatedTestCandidate(**item) for item in metadata["candidates"]]
            return RelatedTestsObservation(
                kind="related_tests",
                ok=bool(metadata["ok"]),
                target_paths=list(metadata["target_paths"]),
                candidates=candidates,
                total=int(metadata["total"]),
                truncated=bool(metadata["truncated"]),
                test_files_total=int(metadata["test_files_total"]),
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return RelatedTestsObservation(
                kind="related_tests",
                ok=False,
                target_paths=[],
                candidates=[],
                total=0,
                truncated=False,
                test_files_total=0,
                message=str(error),
            )

    if isinstance(action, FocusedTestCommandsAction):
        try:
            metadata = suggest_focused_test_commands(
                workspace,
                paths=action.paths,
                max_paths=action.max_paths,
                max_candidates=action.max_candidates,
                max_commands=action.max_commands,
            )
            commands = [FocusedTestCommand(**item) for item in metadata["commands"]]
            return FocusedTestCommandsObservation(
                kind="focused_test_commands",
                ok=bool(metadata["ok"]),
                target_paths=list(metadata["target_paths"]),
                commands=commands,
                total=int(metadata["total"]),
                truncated=bool(metadata["truncated"]),
                related_tests_total=int(metadata["related_tests_total"]),
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return FocusedTestCommandsObservation(
                kind="focused_test_commands",
                ok=False,
                target_paths=[],
                commands=[],
                total=0,
                truncated=False,
                related_tests_total=0,
                message=str(error),
            )

    if isinstance(action, CheckFocusedTestCommandsAction):
        try:
            if action.max_commands > 50:
                raise ValueError("max_commands must be at most 50")
            metadata = suggest_focused_test_commands(
                workspace,
                paths=action.paths,
                max_paths=action.max_paths,
                max_candidates=action.max_candidates,
                max_commands=action.max_commands,
            )
            focused_commands = [FocusedTestCommand(**item) for item in metadata["commands"]]
            checks = [
                build_command_check_observation(workspace, item.command, item.cwd)
                for item in focused_commands
            ]
            failed_count = sum(1 for check in checks if not check.ok)
            return CheckFocusedTestCommandsObservation(
                kind="check_focused_test_commands",
                ok=failed_count == 0,
                checks=checks,
                focused_commands=focused_commands,
                target_paths=list(metadata["target_paths"]),
                total=int(metadata["total"]),
                truncated=bool(metadata["truncated"]),
                max_commands=action.max_commands,
                related_tests_total=int(metadata["related_tests_total"]),
                message=f"Preflighted {len(checks)}/{int(metadata['total'])} focused test command(s); {failed_count} failed.",
            )
        except ValueError as error:
            return CheckFocusedTestCommandsObservation(
                kind="check_focused_test_commands",
                ok=False,
                checks=[],
                focused_commands=[],
                target_paths=[],
                total=0,
                truncated=False,
                max_commands=action.max_commands,
                related_tests_total=0,
                message=str(error),
            )

    if isinstance(action, RunFocusedTestCommandsAction):
        try:
            if action.max_commands > 50:
                raise ValueError("max_commands must be at most 50")
            metadata = suggest_focused_test_commands(
                workspace,
                paths=action.paths,
                max_paths=action.max_paths,
                max_candidates=action.max_candidates,
                max_commands=action.max_commands,
            )
            focused_commands = [FocusedTestCommand(**item) for item in metadata["commands"]]
            runnable_commands = [item for item in focused_commands if item.available]
            skipped_unavailable = len(focused_commands) - len(runnable_commands)
            results: list[CommandResult] = []
            stopped_early = False
            for item in runnable_commands:
                result = execute_run_command_item(
                    workspace,
                    RunCommandItem(
                        command=item.command,
                        cwd=item.cwd,
                        timeout_ms=action.timeout_ms,
                        max_output_chars=action.max_output_chars,
                        extract_output_contexts=action.extract_output_contexts,
                        extract_output_diagnostics=action.extract_output_diagnostics,
                        context_lines=action.context_lines,
                        max_diagnostics=action.max_diagnostics,
                        max_contexts=action.max_contexts,
                        max_bytes_per_context=action.max_bytes_per_context,
                    ),
                    command_timeout_ms,
                )
                results.append(result)
                failed = result.exit_code != 0 or result.timed_out or result.exit_code is None
                if failed and action.stop_on_failure:
                    stopped_early = len(results) < len(runnable_commands)
                    break
            ok = (
                skipped_unavailable == 0
                and len(results) == len(runnable_commands)
                and all(result.exit_code == 0 and not result.timed_out for result in results)
            )
            return RunFocusedTestCommandsObservation(
                kind="run_focused_test_commands",
                ok=ok,
                results=results,
                focused_commands=focused_commands,
                target_paths=list(metadata["target_paths"]),
                total=int(metadata["total"]),
                truncated=bool(metadata["truncated"]),
                max_commands=action.max_commands,
                related_tests_total=int(metadata["related_tests_total"]),
                stopped_early=stopped_early,
                skipped_unavailable=skipped_unavailable,
                message=(
                    f"Ran {len(results)}/{len(runnable_commands)} available focused test command(s); "
                    f"{'all passed' if ok else 'one or more failed or were unavailable'}."
                ),
            )
        except ValueError as error:
            return RunFocusedTestCommandsObservation(
                kind="run_focused_test_commands",
                ok=False,
                results=[],
                focused_commands=[],
                target_paths=[],
                total=0,
                truncated=False,
                max_commands=action.max_commands,
                related_tests_total=0,
                stopped_early=False,
                skipped_unavailable=0,
                message=str(error),
            )

    if isinstance(action, ProjectManifestsAction):
        try:
            metadata = read_project_manifests(
                workspace,
                max_files=action.max_files,
                max_items=action.max_items,
            )
            manifests = [
                ProjectManifest(
                    path=str(item["path"]),
                    kind=str(item["kind"]),
                    ok=bool(item["ok"]),
                    name=str(item["name"]),
                    version=str(item["version"]),
                    items=[ProjectManifestItem(**manifest_item) for manifest_item in item["items"]],
                    item_count=int(item["item_count"]),
                    truncated=bool(item["truncated"]),
                    message=str(item["message"]),
                )
                for item in metadata["manifests"]
            ]
            return ProjectManifestsObservation(
                kind="project_manifests",
                ok=bool(metadata["ok"]),
                manifests=manifests,
                total_files=int(metadata["total_files"]),
                scanned_files=int(metadata["scanned_files"]),
                total_items=int(metadata["total_items"]),
                truncated=bool(metadata["truncated"]),
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return ProjectManifestsObservation(
                kind="project_manifests",
                ok=False,
                manifests=[],
                total_files=0,
                scanned_files=0,
                total_items=0,
                truncated=False,
                message=str(error),
            )

    if isinstance(action, ProjectInstructionsAction):
        try:
            if action.max_bytes < 200:
                raise ValueError("max_bytes must be at least 200.")
            metadata = read_project_instruction_sources(
                workspace,
                max_files=action.max_files,
                max_bytes=action.max_bytes,
            )
            files = [ProjectInstructionSource(**item) for item in metadata["files"]]
            return ProjectInstructionsObservation(
                kind="project_instructions",
                ok=bool(metadata["ok"]),
                files=files,
                total_files=int(metadata["total_files"]),
                scanned_files=int(metadata["scanned_files"]),
                omitted_files=int(metadata["omitted_files"]),
                truncated=bool(metadata["truncated"]),
                text=str(metadata["text"]),
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return ProjectInstructionsObservation(
                kind="project_instructions",
                ok=False,
                files=[],
                total_files=0,
                scanned_files=0,
                omitted_files=0,
                truncated=False,
                text="",
                message=str(error),
            )

    if isinstance(action, ProjectTodosAction):
        try:
            metadata = read_project_todos(
                workspace,
                relative_path=action.path,
                max_items=action.max_items,
                max_files=action.max_files,
            )
            return ProjectTodosObservation(
                kind="project_todos",
                ok=bool(metadata["ok"]),
                todos=[ProjectTodo(**item) for item in metadata["todos"]],
                total=int(metadata["total"]),
                truncated=bool(metadata["truncated"]),
                total_files=int(metadata["total_files"]),
                scanned_files=int(metadata["scanned_files"]),
                path=str(metadata["path"]),
                markers=[str(item) for item in metadata["markers"]],
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return ProjectTodosObservation(
                kind="project_todos",
                ok=False,
                todos=[],
                total=0,
                truncated=False,
                total_files=0,
                scanned_files=0,
                path=action.path or ".",
                markers=[],
                message=str(error),
            )

    if isinstance(action, ProjectOverviewAction):
        try:
            repo_map = build_repo_map(workspace, max_depth=2, max_files=action.max_files, max_symbols=80)
            git_info = read_git_info(workspace)
            commands_metadata = read_project_commands(
                workspace,
                max_commands=action.max_commands,
                max_files=action.max_manifests,
            )
            manifests_metadata = read_project_manifests(
                workspace,
                max_files=action.max_manifests,
                max_items=200,
            )
            instructions_metadata = read_project_instruction_sources(
                workspace,
                max_files=action.max_manifests,
                max_bytes=1_000,
            )
            todos_metadata = read_project_todos(
                workspace,
                max_items=20,
                max_files=action.max_files,
            )
            suggestions = suggest_project_checks(workspace, max_commands=action.max_checks)
            environment = read_environment_info(workspace)
            commands = [ProjectCommand(**item) for item in commands_metadata["commands"]]
            manifests = [
                ProjectManifest(
                    path=str(item["path"]),
                    kind=str(item["kind"]),
                    ok=bool(item["ok"]),
                    name=str(item["name"]),
                    version=str(item["version"]),
                    items=[ProjectManifestItem(**manifest_item) for manifest_item in item["items"]],
                    item_count=int(item["item_count"]),
                    truncated=bool(item["truncated"]),
                    message=str(item["message"]),
                )
                for item in manifests_metadata["manifests"]
            ]
            instruction_sources = [ProjectInstructionSource(**item) for item in instructions_metadata["files"]]
            todos = [ProjectTodo(**item) for item in todos_metadata["todos"]]
            suggested_checks = [SuggestedCheck(**item) for item in suggestions["checks"]]
            tools = [RuntimeToolInfo(**item) for item in environment["tools"]]
            return ProjectOverviewObservation(
                kind="project_overview",
                ok=True,
                project_root=str(environment["project_root"]),
                is_git_repo=bool(git_info["is_git_repo"]),
                git_branch=str(git_info["branch"]),
                git_head=str(git_info["head"]),
                git_upstream=str(git_info["upstream"]),
                git_ahead=int(git_info["ahead"]),
                git_behind=int(git_info["behind"]),
                git_status=str(git_info["status"]),
                tree=list(repo_map["tree"]),
                files=list(repo_map["files"]),
                total_tree_entries=int(repo_map["total_tree_entries"]),
                total_files=int(repo_map["total_files"]),
                repo_truncated=bool(repo_map["truncated"]),
                commands=commands,
                commands_total=int(commands_metadata["total"]),
                commands_truncated=bool(commands_metadata["truncated"]),
                manifests=manifests,
                manifest_files_total=int(manifests_metadata["total_files"]),
                manifests_truncated=bool(manifests_metadata["truncated"]),
                instruction_sources=instruction_sources,
                instruction_files_total=int(instructions_metadata["total_files"]),
                instructions_truncated=bool(instructions_metadata["truncated"]),
                todos=todos,
                todos_total=int(todos_metadata["total"]),
                todos_truncated=bool(todos_metadata["truncated"]),
                suggested_checks=suggested_checks,
                suggested_checks_total=int(suggestions["total"]),
                suggested_checks_truncated=bool(suggestions["truncated"]),
                tools=tools,
                message=(
                    f"Project overview: {int(repo_map['total_files'])} file(s), "
                    f"{int(commands_metadata['total'])} command(s), "
                    f"{int(manifests_metadata['total_files'])} manifest file(s), "
                    f"{int(instructions_metadata['total_files'])} instruction file(s), "
                    f"{int(todos_metadata['total'])} TODO marker(s)."
                ),
            )
        except ValueError as error:
            return ProjectOverviewObservation(
                kind="project_overview",
                ok=False,
                project_root=workspace.root.as_posix(),
                is_git_repo=False,
                git_branch="",
                git_head="",
                git_upstream="",
                git_ahead=0,
                git_behind=0,
                git_status="",
                tree=[],
                files=[],
                total_tree_entries=0,
                total_files=0,
                repo_truncated=False,
                commands=[],
                commands_total=0,
                commands_truncated=False,
                manifests=[],
                manifest_files_total=0,
                manifests_truncated=False,
                instruction_sources=[],
                instruction_files_total=0,
                instructions_truncated=False,
                todos=[],
                todos_total=0,
                todos_truncated=False,
                suggested_checks=[],
                suggested_checks_total=0,
                suggested_checks_truncated=False,
                tools=[],
                message=str(error),
            )

    return None
