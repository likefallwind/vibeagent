from __future__ import annotations

from collections import Counter
from pathlib import Path

from .local_command_workspace import local_command_workspace
from .redaction import redact_sensitive_text
from .workspace_hook_types import ProjectHook
from .workspace_hooks import read_project_hooks


def get_hooks_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    config = read_project_hooks(local_command_workspace(root, "local-hooks"))
    hooks = [_serialize_hook(hook) for hook in config.hooks]
    counts = Counter(str(hook["event"]) for hook in hooks)
    return {
        "projectRoot": str(root),
        "ok": config.error is None,
        "enabled": config.enabled,
        "count": len(hooks),
        "sources": list(config.sources),
        "events": [
            {"event": event, "count": count}
            for event, count in sorted(counts.items())
        ],
        "hooks": hooks,
        "error": config.error or "",
    }


def get_hooks_text(project_root: str | Path = ".") -> str:
    return format_hooks_report_text(get_hooks_report(project_root))


def format_hooks_report_text(report: dict[str, object]) -> str:
    lines = [
        "Hooks:",
        f"  projectRoot: {report['projectRoot']}",
        f"  enabled: {'yes' if report['enabled'] else 'no'}",
        f"  count: {report['count']}",
    ]
    sources = report.get("sources")
    if isinstance(sources, list) and sources:
        lines.append("  sources:")
        lines.extend(f"    - {source}" for source in sources)
    error = report.get("error")
    if error:
        lines.append(f"  error: {error}")
    hooks = report.get("hooks")
    if isinstance(hooks, list) and hooks:
        lines.append("  handlers:")
        for item in hooks:
            if not isinstance(item, dict):
                continue
            lines.append(
                "    - "
                f"{item['event']} matcher={item['matcher']!r} "
                f"type={item['handlerType']} source={item['source']}"
            )
            lines.append(f"      target: {item['target']}")
            lines.append(f"      timeoutMs: {item['timeoutMs']}")
            for key in ("headerNames", "allowedEnvVars", "inputKeys", "environmentNames"):
                values = item.get(key)
                if isinstance(values, list) and values:
                    lines.append(f"      {key}: {', '.join(str(value) for value in values)}")
            if item.get("model"):
                lines.append(f"      model: {item['model']}")
            if item.get("async"):
                lines.append("      async: yes")
            if item.get("asyncRewake"):
                lines.append("      asyncRewake: yes")
            if item.get("continueOnBlock"):
                lines.append("      continueOnBlock: yes")
    return "\n".join(lines)


def _serialize_hook(hook: ProjectHook) -> dict[str, object]:
    item: dict[str, object] = {
        "event": hook.event,
        "matcher": hook.matcher,
        "handlerType": hook.handler_type,
        "target": redact_sensitive_text(hook.handler_target),
        "timeoutMs": hook.timeout_ms,
        "source": hook.source,
    }
    if hook.headers:
        item["headerNames"] = sorted(name for name, _value in hook.headers)
    if hook.allowed_env_vars:
        item["allowedEnvVars"] = sorted(hook.allowed_env_vars)
    if hook.mcp_input:
        item["inputKeys"] = sorted(str(key) for key in hook.mcp_input)
    if hook.environment:
        item["environmentNames"] = sorted(hook.environment)
    if hook.model:
        item["model"] = hook.model
    if hook.async_:
        item["async"] = True
    if hook.async_rewake:
        item["asyncRewake"] = True
    if hook.continue_on_block:
        item["continueOnBlock"] = True
    return item


__all__ = ["format_hooks_report_text", "get_hooks_report", "get_hooks_text"]
