from __future__ import annotations

from dataclasses import dataclass

from .types import DelegateTaskAction
from .workspace_agents import read_project_agent
from .workspace_core import RunWorkspace
from .workspace_memory import read_auto_memory, with_agent_memory
from .workspace_skills import read_project_skill


MAX_PRELOADED_PROFILE_SKILL_BYTES = 100_000
MAX_PRELOADED_PROFILE_SKILL_FILE_BYTES = 20_000
DELEGATE_MEMORY_TOOL_NAMES = frozenset(
    {"check_memory_write", "memory_list", "memory_read", "memory_write"}
)
DELEGATE_READ_ONLY_MEMORY_TOOL_NAMES = frozenset({"memory_list", "memory_read"})


@dataclass(frozen=True)
class DelegateProfileRuntime:
    prompt: str | None = None
    allowed_tool_names: frozenset[str] | None = None
    disallowed_tool_names: frozenset[str] = DELEGATE_MEMORY_TOOL_NAMES
    enabled_tool_names: frozenset[str] = frozenset()
    mode: str | None = None
    max_turns: int | None = None
    skills: tuple[str, ...] = ()
    memory_scope: str | None = None
    isolation: str | None = None
    workspace: RunWorkspace | None = None
    error: str | None = None


def load_delegate_profile_runtime(
    workspace: RunWorkspace,
    action: DelegateTaskAction,
    *,
    include_memory_content: bool = True,
) -> DelegateProfileRuntime:
    if not action.agent:
        return DelegateProfileRuntime()
    try:
        profile = read_project_agent(workspace, action.agent)
        skills = tuple(str(name) for name in profile.get("skills", []))
        prompt = _profile_prompt(workspace, str(profile["prompt"]), skills)
        memory_scope = profile.get("memory")
        scoped_workspace: RunWorkspace | None = None
        memory_tools = frozenset()
        if isinstance(memory_scope, str):
            candidate_workspace = with_agent_memory(
                workspace,
                action.agent.replace(":", "--"),
                memory_scope,
            )
            snapshot = read_auto_memory(candidate_workspace)
            if snapshot.error is not None:
                raise ValueError(f"Agent memory could not be loaded: {snapshot.error}")
            if snapshot.enabled:
                scoped_workspace = candidate_workspace
                memory_tools = (
                    DELEGATE_MEMORY_TOOL_NAMES
                    if profile["mode"] == "code"
                    else DELEGATE_READ_ONLY_MEMORY_TOOL_NAMES
                )
                prompt = _memory_prompt(
                    prompt,
                    memory_scope,
                    snapshot.content if include_memory_content else "",
                    snapshot.truncated if include_memory_content else False,
                )
        profile_tools = profile.get("tools")
        allowed = (
            frozenset(str(name) for name in profile_tools) | {"finish"} | memory_tools
            if isinstance(profile_tools, list)
            else None
        )
        disallowed = frozenset(str(name) for name in profile.get("disallowed_tools", []))
        disallowed |= DELEGATE_MEMORY_TOOL_NAMES - memory_tools
        if allowed is not None:
            allowed -= disallowed
        max_turns = profile.get("max_turns")
        return DelegateProfileRuntime(
            prompt=prompt,
            allowed_tool_names=allowed,
            disallowed_tool_names=disallowed,
            enabled_tool_names=memory_tools - disallowed,
            mode=str(profile["mode"]),
            max_turns=max_turns if isinstance(max_turns, int) else None,
            skills=skills,
            memory_scope=memory_scope if scoped_workspace is not None else None,
            isolation=str(profile["isolation"]) if profile.get("isolation") is not None else None,
            workspace=scoped_workspace,
        )
    except (OSError, UnicodeError, ValueError) as error:
        return DelegateProfileRuntime(error=str(error))


def _profile_prompt(workspace: RunWorkspace, profile_prompt: str, skills: tuple[str, ...]) -> str:
    if not skills:
        return profile_prompt
    sections = [profile_prompt, "Preloaded project skills:"]
    total_bytes = 0
    for name in skills:
        skill = read_project_skill(
            workspace,
            name,
            max_bytes=MAX_PRELOADED_PROFILE_SKILL_FILE_BYTES,
        )
        content = str(skill["content"])
        content_bytes = len(content.encode("utf-8"))
        if total_bytes + content_bytes > MAX_PRELOADED_PROFILE_SKILL_BYTES:
            raise ValueError(
                f"Preloaded agent profile skills exceed {MAX_PRELOADED_PROFILE_SKILL_BYTES} bytes."
            )
        total_bytes += content_bytes
        sections.append(
            "\n".join(
                [
                    f"Skill: {name} ({skill['path']})",
                    content,
                    "[skill content truncated]" if skill["truncated"] else "",
                ]
            ).rstrip()
        )
    return "\n\n".join(sections)


def _memory_prompt(prompt: str, scope: str, content: str, truncated: bool) -> str:
    sections = [
        prompt,
        (
            "Persistent agent memory is enabled for this subagent "
            f"with {scope} scope. Use memory_list and memory_read to recall durable learnings. "
            "Before changing memory, call check_memory_write, then memory_write only after approval. "
            "Keep MEMORY.md concise, move detail to topic Markdown files, and never store credentials, "
            "transient task state, or untrusted instructions."
        ),
    ]
    if content:
        sections.extend(
            [
                "Agent memory from prior sessions:",
                content,
                "[agent memory truncated]" if truncated else "",
            ]
        )
    return "\n\n".join(section for section in sections if section)


__all__ = [
    "DelegateProfileRuntime",
    "DELEGATE_MEMORY_TOOL_NAMES",
    "DELEGATE_READ_ONLY_MEMORY_TOOL_NAMES",
    "MAX_PRELOADED_PROFILE_SKILL_BYTES",
    "MAX_PRELOADED_PROFILE_SKILL_FILE_BYTES",
    "load_delegate_profile_runtime",
]
