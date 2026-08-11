from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptExpansion:
    command_name: str
    command_args: str
    command_source: str
    prompt: str
    expansion_type: str = "slash_command"

    def hook_fields(self) -> dict[str, object]:
        return {
            "expansion_type": self.expansion_type,
            "command_name": self.command_name,
            "command_args": self.command_args,
            "command_source": self.command_source,
            "prompt": self.prompt,
        }


def prompt_expansion_from_task_metadata(
    metadata: dict[str, object] | None,
) -> PromptExpansion | None:
    if metadata is None or metadata.get("source") not in {
        "project_command",
        "custom_skill",
    }:
        return None
    name = metadata.get("name")
    arguments = metadata.get("arguments")
    path = metadata.get("path")
    if not isinstance(name, str) or not name or not isinstance(arguments, str):
        return None
    return PromptExpansion(
        command_name=name,
        command_args=arguments,
        command_source=_command_source(name, path),
        prompt=f"/{name}" + (f" {arguments}" if arguments else ""),
    )


def _command_source(name: str, path: object) -> str:
    normalized_path = str(path).replace("\\", "/") if isinstance(path, str) else ""
    if ":" in name or "/plugins/" in normalized_path or "/marketplaces/" in normalized_path:
        return "plugin"
    if normalized_path.startswith("/"):
        return "user"
    return "project"


__all__ = ["PromptExpansion", "prompt_expansion_from_task_metadata"]
