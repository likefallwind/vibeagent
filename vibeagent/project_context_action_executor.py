from __future__ import annotations

from .project_context_check_actions import execute_project_context_check_action
from .project_overview_action_executor import execute_project_overview_action
from .tool_catalog import get_tool_search_report
from .types import (
    AgentAction,
    Observation,
    ProjectCommand,
    ProjectCommandsAction,
    ProjectCommandsObservation,
    ProjectAgentProfile,
    ProjectAgentsAction,
    ProjectAgentsObservation,
    ProjectInstructionSource,
    ProjectInstructionsAction,
    ProjectInstructionsObservation,
    ProjectSkill,
    ProjectSkillsAction,
    ProjectSkillsObservation,
    ProjectManifest,
    ProjectManifestItem,
    ProjectManifestsAction,
    ProjectManifestsObservation,
    ProjectOverviewAction,
    ProjectTodo,
    ProjectTodosAction,
    ProjectTodosObservation,
    SkillAction,
    SkillObservation,
    ToolSearchAction,
    ToolSearchObservation,
)
from .workspace import (
    read_project_commands,
    read_project_agents,
    read_project_instruction_sources,
    read_project_skill,
    read_project_skills,
    read_project_manifests,
    read_project_todos,
)


def execute_project_context_action(
    workspace,
    action: AgentAction,
    command_timeout_ms: int = 30_000,
) -> Observation | None:
    check_observation = execute_project_context_check_action(workspace, action, command_timeout_ms)
    if check_observation is not None:
        return check_observation

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

    if isinstance(action, ProjectSkillsAction):
        try:
            metadata = read_project_skills(workspace, max_skills=action.max_skills)
            return ProjectSkillsObservation(
                kind="project_skills",
                ok=bool(metadata["ok"]),
                skills=[ProjectSkill(**item) for item in metadata["skills"]],
                total=int(metadata["total"]),
                truncated=bool(metadata["truncated"]),
                invalid=int(metadata["invalid"]),
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return ProjectSkillsObservation(
                kind="project_skills", ok=False, skills=[], total=0, truncated=False, invalid=0, message=str(error)
            )

    if isinstance(action, ProjectAgentsAction):
        try:
            metadata = read_project_agents(workspace, max_agents=action.max_agents)
            return ProjectAgentsObservation(
                kind="project_agents",
                ok=bool(metadata["ok"]),
                agents=[ProjectAgentProfile(**item) for item in metadata["agents"]],
                total=int(metadata["total"]),
                truncated=bool(metadata["truncated"]),
                invalid=int(metadata["invalid"]),
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return ProjectAgentsObservation(
                kind="project_agents", ok=False, agents=[], total=0, truncated=False, invalid=0, message=str(error)
            )

    if isinstance(action, SkillAction):
        try:
            metadata = read_project_skill(workspace, action.name, max_bytes=action.max_bytes)
            return SkillObservation(
                kind="skill",
                ok=True,
                name=str(metadata["name"]),
                description=str(metadata["description"]),
                path=str(metadata["path"]),
                source=str(metadata["source"]),
                content=str(metadata["content"]),
                bytes=int(metadata["bytes"]),
                truncated=bool(metadata["truncated"]),
                max_bytes=int(metadata["max_bytes"]),
                message=str(metadata["message"]),
            )
        except (OSError, ValueError) as error:
            return SkillObservation(
                kind="skill",
                ok=False,
                name=action.name,
                description="",
                path="",
                source="",
                content="",
                bytes=0,
                truncated=False,
                max_bytes=action.max_bytes,
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
        return execute_project_overview_action(workspace, action)

    return None
