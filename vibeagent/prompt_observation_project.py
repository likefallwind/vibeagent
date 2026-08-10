from __future__ import annotations

from .prompt_observation_mcp import format_mcp_observation
from .prompt_observation_project_commands import (
    COMMAND_OBSERVATION_KINDS,
    format_command_metadata as _format_command_metadata,
    format_project_command_observation,
)
from .prompt_observation_utils import truncate


def format_project_observation(index: int, observation: object) -> str | None:
    if observation.kind == "delegate_task":
        return _format_delegate_task(index, observation)
    if observation.kind in COMMAND_OBSERVATION_KINDS:
        return format_project_command_observation(index, observation)
    if observation.kind == "tool_search":
        return _format_tool_search(index, observation)
    if observation.kind == "related_tests":
        return _format_related_tests(index, observation)
    if observation.kind == "project_manifests":
        return _format_project_manifests(index, observation)
    if observation.kind == "project_instructions":
        return _format_project_instructions(index, observation)
    if observation.kind == "project_skills":
        return _format_project_skills(index, observation)
    if observation.kind == "project_agents":
        return _format_project_agents(index, observation)
    if observation.kind == "list_agents":
        return _format_list_agents(index, observation)
    if observation.kind == "skill":
        return _format_skill(index, observation)
    if observation.kind == "project_todos":
        return _format_project_todos(index, observation)
    if observation.kind == "project_overview":
        return _format_project_overview(index, observation)
    return format_mcp_observation(index, observation)


def _format_delegate_task(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. delegate_task {observation.task_id or '.'}: {observation.message} "
            f"ok={str(observation.ok).lower()} mode={observation.mode} "
            f"background={str(observation.background).lower()} running={str(observation.running).lower()} "
            f"iterations={observation.iterations}"
        )
    ]
    if observation.agent:
        parts.append(f"profile: {observation.agent}")
    if getattr(observation, "isolation", None):
        parts.append(
            f"isolation: {observation.isolation} worktree={observation.worktree_path or '.'} "
            f"branch={observation.worktree_branch or '.'} preserved={str(observation.worktree_preserved).lower()}"
        )
    if observation.summary:
        parts.append(f"summary:\n{truncate(observation.summary)}")
    return "\n".join(parts)


def _format_tool_search(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. tool_search: {observation.message} "
            f"query={observation.query} "
            f"shown={observation.shown}/{observation.total} "
            f"truncated={str(observation.truncated).lower()}"
        )
    ]
    if observation.category:
        parts.append(f"category: {observation.category}")
    if observation.approval_required is not None:
        parts.append(f"approval_required: {str(observation.approval_required).lower()}")
    for match in observation.matches:
        name = str(match.get("name", ""))
        if not name:
            continue
        matched_fields = match.get("matchedFields")
        matched_text = ", ".join(str(item) for item in matched_fields) if isinstance(matched_fields, list) else "."
        required = match.get("required")
        required_text = ", ".join(str(item) for item in required) if isinstance(required, list) and required else "."
        parts.append(
            (
                f"tool: name={name} category={match.get('category', 'other')} "
                f"approvalRequired={str(bool(match.get('approvalRequired'))).lower()} "
                f"score={match.get('score', 0)} matched={matched_text} required={required_text} "
                f"description={match.get('description', '')}"
            )
        )
    if observation.suggestions and not observation.matches:
        parts.append("suggestions: " + ", ".join(observation.suggestions))
    return "\n".join(parts)


def _format_related_tests(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. related_tests: {observation.message} "
            f"ok={str(observation.ok).lower()} "
            f"targets={len(observation.target_paths)} "
            f"shown={len(observation.candidates)}/{observation.total} "
            f"testFiles={observation.test_files_total} "
            f"truncated={str(observation.truncated).lower()}"
        )
    ]
    if observation.target_paths:
        parts.append("target_paths:\n" + "\n".join(observation.target_paths[:120]))
    for candidate in observation.candidates:
        parts.append(
            (
                f"candidate: source={candidate.source_path} test={candidate.test_path} "
                f"score={candidate.score} reason={candidate.reason}"
            )
        )
    return "\n".join(parts)


def _format_project_manifests(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. project_manifests: {observation.message} "
            f"files={observation.scanned_files}/{observation.total_files} "
            f"items={observation.total_items} "
            f"truncated={str(observation.truncated).lower()}"
        )
    ]
    for manifest in observation.manifests[:40]:
        parts.append(
            (
                f"manifest: {manifest.path} kind={manifest.kind} ok={str(manifest.ok).lower()} "
                f"name={manifest.name or '.'} version={manifest.version or '.'} "
                f"items={len(manifest.items)}/{manifest.item_count} "
                f"truncated={str(manifest.truncated).lower()} message={manifest.message}"
            )
        )
        for item in manifest.items[:120]:
            parts.append(f"item: group={item.group} name={item.name} value={item.value or '.'}")
    return "\n".join(parts)


def _format_project_instructions(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. project_instructions: {observation.message} "
            f"files={observation.scanned_files}/{observation.total_files} "
            f"omitted={observation.omitted_files} "
            f"truncated={str(observation.truncated).lower()}"
        ),
        f"ok: {str(observation.ok).lower()}",
    ]
    for source in observation.files:
        parts.append(
            (
                f"source: {source.path} scope={source.scope} "
                f"bytes={source.bytes} chars={source.chars} "
                f"empty={str(source.empty).lower()} included={str(source.included).lower()} "
                f"reason={source.reason} owner={source.owner_path or '.'} parent={source.parent_path or '.'} "
                f"message={source.message}"
            )
        )
    if observation.text:
        parts.append(f"instructions:\n{truncate(observation.text)}")
    return "\n".join(parts)


def _format_project_skills(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. project_skills: {observation.message} "
            f"shown={len(observation.skills)}/{observation.total} "
            f"invalid={observation.invalid} truncated={str(observation.truncated).lower()}"
        ),
        f"ok: {str(observation.ok).lower()}",
    ]
    for skill in observation.skills:
        parts.append(
            f"skill: name={skill.name} source={skill.source} path={skill.path} "
            f"available={str(skill.available).lower()} description={skill.description or '.'} message={skill.message}"
        )
    return "\n".join(parts)


def _format_project_agents(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. project_agents: {observation.message} "
            f"shown={len(observation.agents)}/{observation.total} "
            f"invalid={observation.invalid} truncated={str(observation.truncated).lower()}"
        ),
        f"ok: {str(observation.ok).lower()}",
    ]
    for agent in observation.agents:
        tools = ",".join(agent.tools) if agent.tools is not None else "default"
        denied = ",".join(agent.disallowed_tools) or "none"
        skills = ",".join(agent.skills) or "none"
        isolation = getattr(agent, "isolation", None) or "none"
        parts.append(
            f"agent: name={agent.name} mode={agent.mode} tools={tools} disallowedTools={denied} "
            f"maxTurns={agent.max_turns or 'default'} skills={skills} memory={agent.memory or 'none'} "
            f"source={agent.source} path={agent.path} "
            f"isolation={isolation} available={str(agent.available).lower()} "
            f"description={agent.description or '.'} message={agent.message}"
        )
    return "\n".join(parts)


def _format_list_agents(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. list_agents: {observation.message} "
            f"shown={len(observation.agents)}/{observation.total} "
            f"invalid={observation.invalid} truncated={str(observation.truncated).lower()}"
        ),
        f"ok: {str(observation.ok).lower()}",
    ]
    for agent in observation.agents:
        parts.append(
            f"agent: id={agent.id} status={agent.status} mode={agent.mode} "
            f"profile={agent.agent or '.'} background={str(agent.background).lower()} "
            f"runs={agent.runs} resumable={str(agent.resumable).lower()} "
            f"isolation={getattr(agent, 'isolation', None) or 'none'} "
            f"worktree={getattr(agent, 'worktree_path', None) or '.'} "
            f"branch={getattr(agent, 'worktree_branch', None) or '.'} "
            f"worktreePreserved={str(bool(getattr(agent, 'worktree_preserved', False))).lower()} task={agent.task}"
        )
    return "\n".join(parts)


def _format_skill(index: int, observation: object) -> str:
    parts = [
        f"{index}. skill {observation.name}: {observation.message}",
        f"ok: {str(observation.ok).lower()}",
        f"path: {observation.path or 'none'} source={observation.source or 'none'}",
        f"bytes: {observation.bytes} maxBytes={observation.max_bytes} truncated={str(observation.truncated).lower()}",
        f"description: {observation.description or 'none'}",
    ]
    if observation.arguments:
        parts.append(f"arguments: {observation.arguments}")
    if observation.content:
        parts.append(f"instructions:\n{truncate(observation.content)}")
    return "\n".join(parts)


def _format_project_todos(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. project_todos: {observation.message} "
            f"path={observation.path} "
            f"shown={len(observation.todos)}/{observation.total} "
            f"files={observation.scanned_files}/{observation.total_files} "
            f"truncated={str(observation.truncated).lower()}"
        ),
        f"markers: {', '.join(observation.markers) if observation.markers else '.'}",
    ]
    for todo in observation.todos:
        parts.append(f"todo: {todo.path}:{todo.line} [{todo.marker}] {todo.text}")
    return "\n".join(parts)


def _format_project_overview(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. project_overview: {observation.message} "
            f"root={observation.project_root} "
            f"git={str(observation.is_git_repo).lower()} "
            f"branch={observation.git_branch or '.'} head={observation.git_head or '.'} "
            f"upstream={observation.git_upstream or '.'} "
            f"ahead={observation.git_ahead} behind={observation.git_behind}"
        ),
        (
            f"repo: files={len(observation.files)}/{observation.total_files} "
            f"tree={len(observation.tree)}/{observation.total_tree_entries} "
            f"truncated={str(observation.repo_truncated).lower()}"
        ),
    ]
    if observation.git_status.strip():
        parts.append(f"git_status:\n{truncate(observation.git_status, 2000)}")
    if observation.tree:
        parts.append("tree:\n" + "\n".join(observation.tree[:80]))
    if observation.commands:
        parts.append(
            (
                f"commands shown={len(observation.commands)}/{observation.commands_total} "
                f"truncated={str(observation.commands_truncated).lower()}"
            )
        )
        for command in observation.commands[:40]:
            parts.append(
                _format_command_metadata(
                    "command",
                    command,
                    [("source", command.source), ("file", command.file)],
                )
            )
    if observation.manifests:
        parts.append(
            (
                f"manifests shown={len(observation.manifests)}/{observation.manifest_files_total} "
                f"truncated={str(observation.manifests_truncated).lower()}"
            )
        )
        for manifest in observation.manifests[:20]:
            parts.append(
                (
                    f"manifest: {manifest.path} kind={manifest.kind} ok={str(manifest.ok).lower()} "
                    f"name={manifest.name or '.'} items={manifest.item_count}"
                )
            )
    if observation.instruction_sources:
        parts.append(
            (
                f"instructions shown={len(observation.instruction_sources)}/{observation.instruction_files_total} "
                f"truncated={str(observation.instructions_truncated).lower()}"
            )
        )
        for source in observation.instruction_sources[:20]:
            parts.append(
                (
                    f"instruction: {source.path} scope={source.scope or '.'} "
                    f"included={str(source.included).lower()} empty={str(source.empty).lower()} "
                    f"bytes={source.bytes} chars={source.chars} reason={source.reason} "
                    f"owner={source.owner_path or '.'} parent={source.parent_path or '.'}"
                )
            )
    if observation.todos:
        parts.append(
            (
                f"todos shown={len(observation.todos)}/{observation.todos_total} "
                f"truncated={str(observation.todos_truncated).lower()}"
            )
        )
        for todo in observation.todos[:20]:
            parts.append(f"todo: {todo.path}:{todo.line} [{todo.marker}] {todo.text}")
    if observation.suggested_checks:
        parts.append(
            (
                f"suggested_checks shown={len(observation.suggested_checks)}/{observation.suggested_checks_total} "
                f"truncated={str(observation.suggested_checks_truncated).lower()}"
            )
        )
        for check in observation.suggested_checks[:20]:
            parts.append(_format_command_metadata("check", check, [("reason", check.reason)]))
    if observation.skills:
        parts.append(
            f"skills shown={len(observation.skills)}/{observation.skills_total} "
            f"truncated={str(observation.skills_truncated).lower()}"
        )
        for skill in observation.skills[:20]:
            parts.append(
                f"skill: name={skill.name} available={str(skill.available).lower()} "
                f"source={skill.source} description={skill.description or '.'}"
            )
    if observation.tools:
        parts.append(
            "tools: "
            + ", ".join(
                f"{tool.name}={'yes' if tool.available else 'no'}"
                for tool in observation.tools[:20]
            )
        )
    return "\n".join(parts)


__all__ = ["format_project_observation"]
