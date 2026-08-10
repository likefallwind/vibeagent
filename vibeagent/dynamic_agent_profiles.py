from __future__ import annotations

from dataclasses import dataclass
import json

from .workspace_agent_profile_parser import parse_agent_mapping


MAX_DYNAMIC_AGENTS = 100
MAX_DYNAMIC_AGENTS_BYTES = 256_000
MAX_DYNAMIC_AGENT_PROMPT_BYTES = 64_000


@dataclass(frozen=True)
class DynamicAgentProfile:
    name: str
    description: str
    prompt: str
    mode: str
    model: str | None
    effort: str | None
    tools: tuple[str, ...] | None
    disallowed_tools: tuple[str, ...]
    max_turns: int | None
    skills: tuple[str, ...]
    memory: str | None
    isolation: str | None

    def metadata(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "mode": self.mode,
            "model": self.model,
            "effort": self.effort,
            "tools": list(self.tools) if self.tools is not None else None,
            "disallowed_tools": list(self.disallowed_tools),
            "max_turns": self.max_turns,
            "skills": list(self.skills),
            "memory": self.memory,
            "isolation": self.isolation,
        }


def parse_dynamic_agent_profiles(value: str | None) -> tuple[DynamicAgentProfile, ...]:
    if value is None:
        return ()
    raw = value.encode("utf-8")
    if len(raw) > MAX_DYNAMIC_AGENTS_BYTES:
        raise ValueError(f"--agents JSON must not exceed {MAX_DYNAMIC_AGENTS_BYTES} bytes.")
    try:
        payload = json.loads(value, object_pairs_hook=_unique_json_object)
    except json.JSONDecodeError as error:
        raise ValueError(f"Could not parse --agents JSON: {error}") from error
    except ValueError as error:
        raise ValueError(f"Could not parse --agents JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("--agents must contain a JSON object keyed by agent name.")
    if len(payload) > MAX_DYNAMIC_AGENTS:
        raise ValueError(f"--agents may define at most {MAX_DYNAMIC_AGENTS} agents.")

    profiles: list[DynamicAgentProfile] = []
    for name, definition in payload.items():
        if not isinstance(name, str) or not isinstance(definition, dict):
            raise ValueError("--agents entries must map string names to JSON objects.")
        try:
            metadata, prompt = parse_agent_mapping(name, definition)
        except ValueError as error:
            raise ValueError(f"Invalid --agents profile {name!r}: {error}") from error
        if len(prompt.encode("utf-8")) > MAX_DYNAMIC_AGENT_PROMPT_BYTES:
            raise ValueError(
                f"Invalid --agents profile {name!r}: prompt must not exceed "
                f"{MAX_DYNAMIC_AGENT_PROMPT_BYTES} bytes."
            )
        tools = metadata.get("tools")
        profiles.append(
            DynamicAgentProfile(
                name=str(metadata["name"]),
                description=str(metadata["description"]),
                prompt=prompt,
                mode=str(metadata["mode"]),
                model=str(metadata["model"]) if metadata.get("model") is not None else None,
                effort=str(metadata["effort"]) if metadata.get("effort") is not None else None,
                tools=tuple(str(item) for item in tools) if isinstance(tools, list) else None,
                disallowed_tools=tuple(str(item) for item in metadata["disallowed_tools"]),
                max_turns=metadata["max_turns"] if isinstance(metadata.get("max_turns"), int) else None,
                skills=tuple(str(item) for item in metadata["skills"]),
                memory=str(metadata["memory"]) if metadata.get("memory") is not None else None,
                isolation=str(metadata["isolation"]) if metadata.get("isolation") is not None else None,
            )
        )
    return tuple(profiles)


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key {key!r}")
        result[key] = value
    return result


__all__ = ["DynamicAgentProfile", "parse_dynamic_agent_profiles"]
