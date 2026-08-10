from __future__ import annotations

from .prompt_observation_utils import truncate


def format_mcp_observation(index: int, observation: object) -> str | None:
    if observation.kind == "mcp_servers":
        return _format_mcp_servers(index, observation)
    if observation.kind == "mcp_tools":
        return _format_mcp_tools(index, observation)
    if observation.kind == "mcp_resources":
        return _format_mcp_resources(index, observation)
    if observation.kind == "mcp_read_resource":
        return _format_mcp_read_resource(index, observation)
    if observation.kind == "mcp_call":
        return _format_mcp_call(index, observation)
    return None


def _format_mcp_servers(index: int, observation: object) -> str:
    parts = [
        f"{index}. mcp_servers: {observation.message} shown={len(observation.servers)}/{observation.total} truncated={str(observation.truncated).lower()}",
        f"ok: {str(observation.ok).lower()} config={observation.config_path}",
    ]
    for server in observation.servers:
        if server.transport == "http":
            parts.append(
                f"server: name={server.name} transport=http endpoint={server.endpoint} headerKeys={server.header_keys} protocolVersion={server.protocol_version}"
            )
        else:
            parts.append(
                f"server: name={server.name} transport=stdio command={server.command} argCount={server.arg_count} cwd={server.cwd} envKeys={server.env_keys}"
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


def _format_mcp_resources(index: int, observation: object) -> str:
    parts = [
        f"{index}. mcp_resources {observation.server}: {observation.message}",
        f"ok: {str(observation.ok).lower()} resources={len(observation.resources)}/{observation.resource_total} templates={len(observation.templates)}/{observation.template_total} total={observation.total} truncated={str(observation.truncated).lower()} timeoutMs={observation.timeout_ms}",
        f"error: {observation.error or 'none'}",
    ]
    for resource in observation.resources:
        parts.append(
            f"resource: uri={resource.uri} name={resource.name or '.'} title={resource.title or '.'} mimeType={resource.mime_type or '.'} size={resource.size if resource.size is not None else 'unknown'} description={resource.description or '.'}"
        )
    for template in observation.templates:
        parts.append(
            f"resourceTemplate: uriTemplate={template.uri_template} name={template.name or '.'} title={template.title or '.'} mimeType={template.mime_type or '.'} description={template.description or '.'}"
        )
    return "\n".join(parts)


def _format_mcp_read_resource(index: int, observation: object) -> str:
    parts = [
        f"{index}. mcp_read_resource {observation.server}/{observation.uri}: {observation.message}",
        f"ok: {str(observation.ok).lower()} templateUri={observation.template_uri or 'none'} mimeTypes={observation.mime_types} truncated={str(observation.truncated).lower()} maxOutputChars={observation.max_output_chars} timeoutMs={observation.timeout_ms}",
        f"error: {observation.error or 'none'}",
    ]
    if observation.output:
        parts.append(f"output:\n{truncate(observation.output)}")
    return "\n".join(parts)
