from __future__ import annotations

from .prompt_observation_utils import truncate


def format_mcp_observation(index: int, observation: object) -> str | None:
    if observation.kind == "mcp_servers":
        return _format_mcp_servers(index, observation)
    if observation.kind == "mcp_tools":
        return _format_mcp_tools(index, observation)
    if observation.kind == "mcp_call":
        return _format_mcp_call(index, observation)
    return None


def _format_mcp_servers(index: int, observation: object) -> str:
    parts = [
        f"{index}. mcp_servers: {observation.message} shown={len(observation.servers)}/{observation.total} truncated={str(observation.truncated).lower()}",
        f"ok: {str(observation.ok).lower()} config={observation.config_path}",
    ]
    for server in observation.servers:
        parts.append(
            f"server: name={server.name} command={server.command} argCount={server.arg_count} cwd={server.cwd} envKeys={server.env_keys}"
        )
    return "\n".join(parts)


def _format_mcp_tools(index: int, observation: object) -> str:
    parts = [
        f"{index}. mcp_tools {observation.server}: {observation.message}",
        f"ok: {str(observation.ok).lower()} shown={len(observation.tools)}/{observation.total} truncated={str(observation.truncated).lower()} timeoutMs={observation.timeout_ms}",
        f"error: {observation.error or 'none'}",
    ]
    for tool in observation.tools:
        parts.append(
            f"tool: name={tool.name} title={tool.title or '.'} description={tool.description or '.'} inputSchema={tool.input_schema}"
        )
    return "\n".join(parts)


def _format_mcp_call(index: int, observation: object) -> str:
    parts = [
        f"{index}. mcp_call {observation.server}/{observation.name}: {observation.message}",
        f"ok: {str(observation.ok).lower()} isError={str(observation.is_error).lower()} truncated={str(observation.truncated).lower()} maxOutputChars={observation.max_output_chars} timeoutMs={observation.timeout_ms}",
        f"error: {observation.error or 'none'}",
    ]
    if observation.output:
        parts.append(f"output:\n{truncate(observation.output)}")
    return "\n".join(parts)
