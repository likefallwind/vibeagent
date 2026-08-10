from __future__ import annotations

from dataclasses import dataclass

from .types import DelegateTaskAction
from .workspace_agents import read_project_agent
from .workspace_core import RunWorkspace
from .workspace_skills import read_project_skill


MAX_PRELOADED_PROFILE_SKILL_BYTES = 100_000
MAX_PRELOADED_PROFILE_SKILL_FILE_BYTES = 20_000


@dataclass(frozen=True)
class DelegateProfileRuntime:
    prompt: str | None = None
    allowed_tool_names: frozenset[str] | None = None
    disallowed_tool_names: frozenset[str] = frozenset()
    mode: str | None = None
    max_turns: int | None = None
    skills: tuple[str, ...] = ()
    error: str | None = None


def load_delegate_profile_runtime(
    workspace: RunWorkspace,
    action: DelegateTaskAction,
) -> DelegateProfileRuntime:
    if not action.agent:
        return DelegateProfileRuntime()
    try:
        profile = read_project_agent(workspace, action.agent)
        skills = tuple(str(name) for name in profile.get("skills", []))
        prompt = _profile_prompt(workspace, str(profile["prompt"]), skills)
        profile_tools = profile.get("tools")
        allowed = (
            frozenset(str(name) for name in profile_tools) | {"finish"}
            if isinstance(profile_tools, list)
            else None
        )
        disallowed = frozenset(str(name) for name in profile.get("disallowed_tools", []))
        if allowed is not None:
            allowed -= disallowed
        max_turns = profile.get("max_turns")
        return DelegateProfileRuntime(
            prompt=prompt,
            allowed_tool_names=allowed,
            disallowed_tool_names=disallowed,
            mode=str(profile["mode"]),
            max_turns=max_turns if isinstance(max_turns, int) else None,
            skills=skills,
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


__all__ = [
    "DelegateProfileRuntime",
    "MAX_PRELOADED_PROFILE_SKILL_BYTES",
    "MAX_PRELOADED_PROFILE_SKILL_FILE_BYTES",
    "load_delegate_profile_runtime",
]
