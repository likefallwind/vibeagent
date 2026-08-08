from __future__ import annotations

from .prompt_observation_process import format_process_observation
from .prompt_observation_utils import truncate


def format_runtime_observation(index: int, observation: object) -> str | None:
    if observation.kind in {"command_check", "check_start_command"}:
        return "\n".join(
            [
                f"{index}. {observation.kind}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"command: {observation.command}",
                f"cwd: {observation.cwd}",
                f"cwdOk: {str(observation.cwd_ok).lower()}",
                f"blocked: {str(observation.blocked).lower()}",
                f"blockReason: {observation.block_reason or 'none'}",
                f"executableAvailable: {str(observation.executable_available).lower()}",
                f"missingTool: {observation.missing_tool or 'none'}",
            ]
        )

    if observation.kind == "check_run_commands":
        parts = [
            f"{index}. check_run_commands: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
        ]
        for check in observation.checks:
            parts.extend(
                [
                    f"command: {check.command}",
                    f"cwd: {check.cwd}",
                    f"ok: {str(check.ok).lower()} cwdOk={str(check.cwd_ok).lower()} blocked={str(check.blocked).lower()} executableAvailable={str(check.executable_available).lower()}",
                    f"blockReason: {check.block_reason or 'none'} missingTool={check.missing_tool or 'none'} message={check.message}",
                ]
            )
        return "\n".join(parts)

    if observation.kind == "port_check":
        return "\n".join(
            [
                f"{index}. port_check {observation.host}:{observation.port}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"reachable: {str(observation.reachable).lower()}",
                f"timeoutMs: {observation.timeout_ms}",
                f"error: {observation.error or 'none'}",
            ]
        )

    if observation.kind == "http_check":
        parts = [
            f"{index}. http_check {observation.url}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"reachable: {str(observation.reachable).lower()}",
            f"status: {observation.status if observation.status is not None else 'none'}",
            f"reason: {observation.reason or 'none'}",
            f"finalUrl: {observation.final_url or 'none'}",
            f"timeoutMs: {observation.timeout_ms}",
            f"matched: {str(observation.matched).lower()}",
            f"matchedPattern: {observation.matched_pattern or 'none'}",
            f"bodyTruncated: {str(observation.body_truncated).lower()}",
            f"maxBodyChars: {observation.max_body_chars}",
            f"error: {observation.error or 'none'}",
        ]
        if observation.body:
            parts.append(f"body:\n{observation.body}")
        return "\n".join(parts)

    if observation.kind == "http_fetch":
        parts = [
            f"{index}. http_fetch {observation.url}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"reachable: {str(observation.reachable).lower()}",
            f"status: {observation.status if observation.status is not None else 'none'}",
            f"reason: {observation.reason or 'none'}",
            f"contentType: {observation.content_type or 'none'}",
            f"finalUrl: {observation.final_url or 'none'}",
            f"timeoutMs: {observation.timeout_ms}",
            f"bodyTruncated: {str(observation.body_truncated).lower()}",
            f"maxBodyChars: {observation.max_body_chars}",
            f"error: {observation.error or 'none'}",
        ]
        if observation.body:
            parts.append(f"body:\n{observation.body}")
        return "\n".join(parts)

    if observation.kind == "web_fetch":
        parts = [
            f"{index}. web_fetch {observation.url}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"status: {observation.status if observation.status is not None else 'none'}",
            f"contentType: {observation.content_type or 'none'}",
            f"title: {observation.title or 'none'}",
            f"finalUrl: {observation.final_url or 'none'}",
            f"textTruncated: {str(observation.text_truncated).lower()}",
            f"maxTextChars: {observation.max_text_chars}",
            f"error: {observation.error or 'none'}",
        ]
        if observation.prompt:
            parts.append(f"prompt: {observation.prompt}")
        if observation.text:
            parts.append(f"text:\n{observation.text}")
        return "\n".join(parts)

    if observation.kind == "web_search":
        parts = [
            f"{index}. web_search {observation.query}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"results: {len(observation.results)}/{observation.total_results}",
            f"resultsTruncated: {str(observation.results_truncated).lower()}",
            f"allowedDomains: {', '.join(observation.allowed_domains) or 'none'}",
            f"blockedDomains: {', '.join(observation.blocked_domains) or 'none'}",
            f"error: {observation.error or 'none'}",
        ]
        for result in observation.results:
            parts.append(f"result: {result.title}\nurl: {result.url}\nsnippet: {result.snippet or 'none'}")
        return "\n".join(parts)

    if observation.kind == "environment_info":
        parts = [
            (
                f"{index}. environment_info: {observation.message} "
                f"ok={str(observation.ok).lower()} "
                f"projectRoot={observation.project_root} "
                f"python={observation.python_version} "
                f"platform={observation.platform} "
                f"gitRepo={str(observation.is_git_repo).lower()}"
            ),
            f"pythonExecutable: {observation.python_executable or 'unknown'}",
        ]
        for tool in observation.tools:
            parts.append(
                (
                    f"tool: {tool.name} available={str(tool.available).lower()} "
                    f"path={tool.path or '.'} version={tool.version or '.'} message={tool.message}"
                )
            )
        return "\n".join(parts)

    return format_process_observation(index, observation)


__all__ = ["format_runtime_observation"]
