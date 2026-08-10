from __future__ import annotations

from typing import Any

import yaml


MAX_AGENT_FRONTMATTER_BYTES = 128_000


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    loader.flatten_mapping(node)
    result: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as error:
            raise ValueError("Agent profile frontmatter keys must be scalar values.") from error
        if duplicate:
            raise ValueError(f"Agent profile frontmatter contains duplicate key {key!r}.")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def parse_agent_frontmatter(content: str) -> tuple[dict[str, object], str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content
    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing_index is None:
        return {}, content
    raw = "\n".join(lines[1:closing_index])
    if len(raw.encode("utf-8")) > MAX_AGENT_FRONTMATTER_BYTES:
        raise ValueError(
            f"Agent profile frontmatter exceeds {MAX_AGENT_FRONTMATTER_BYTES} bytes."
        )
    try:
        loaded: Any = yaml.load(raw, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as error:
        raise ValueError(f"Could not parse agent profile YAML frontmatter: {error}") from error
    if loaded is None:
        metadata: dict[str, object] = {}
    elif not isinstance(loaded, dict) or not all(isinstance(key, str) for key in loaded):
        raise ValueError("Agent profile frontmatter must contain an object with string keys.")
    else:
        metadata = loaded
    return metadata, "\n".join(lines[closing_index + 1 :])


__all__ = ["MAX_AGENT_FRONTMATTER_BYTES", "parse_agent_frontmatter"]
