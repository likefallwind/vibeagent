from __future__ import annotations

from .types import (
    ProjectCommand,
    ProjectInstructionSource,
    ProjectManifest,
    ProjectManifestItem,
    ProjectOverviewAction,
    ProjectOverviewObservation,
    ProjectSkill,
    ProjectTodo,
    RuntimeToolInfo,
    SuggestedCheck,
)
from .workspace import (
    build_repo_map,
    read_environment_info,
    read_git_info,
    read_project_commands,
    read_project_instruction_sources,
    read_project_manifests,
    read_project_skills,
    read_project_todos,
    suggest_project_checks,
)


def execute_project_overview_action(workspace, action: ProjectOverviewAction) -> ProjectOverviewObservation:
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
        skills_metadata = read_project_skills(workspace, max_skills=20)
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
        skills = [ProjectSkill(**item) for item in skills_metadata["skills"]]
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
            skills=skills,
            skills_total=int(skills_metadata["total"]),
            skills_truncated=bool(skills_metadata["truncated"]),
            tools=tools,
            message=(
                f"Project overview: {int(repo_map['total_files'])} file(s), "
                f"{int(commands_metadata['total'])} command(s), "
                f"{int(manifests_metadata['total_files'])} manifest file(s), "
                f"{int(instructions_metadata['total_files'])} instruction file(s), "
                f"{int(skills_metadata['total'])} project skill(s), "
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
            skills=[],
            skills_total=0,
            skills_truncated=False,
            tools=[],
            message=str(error),
        )
