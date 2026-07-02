from __future__ import annotations


def format_code_deps_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = files.get("items") if isinstance(files.get("items"), list) else []
    lines = [
        "Code dependencies:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or '.'}",
        f"  files: {files.get('shown', 0)}/{files.get('total', 0)}",
        f"  truncated: {'yes' if bool(files.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if items:
        lines.append("  files:")
        for item in items:
            if not isinstance(item, dict):
                continue
            dependencies = item.get("dependencies") if isinstance(item.get("dependencies"), list) else []
            imports = item.get("imports") if isinstance(item.get("imports"), list) else []
            lines.append(f"    - {item.get('path')} ({item.get('language')}): {'ok' if bool(item.get('ok')) else 'failed'} - {item.get('message')}")
            lines.append(f"      dependencies: {', '.join(str(value) for value in dependencies) if dependencies else '-'}")
            if imports:
                lines.append("      imports:")
                for import_ref in imports:
                    if isinstance(import_ref, dict):
                        lines.append(f"        - line {import_ref.get('line')} {import_ref.get('kind')}: {import_ref.get('source')} :: {import_ref.get('raw')}")
            else:
                lines.append("      imports: none")
    else:
        lines.append("  files: none")
    return "\n".join(lines)


def format_code_refs_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    references = report.get("references") if isinstance(report.get("references"), dict) else {}
    items = references.get("items") if isinstance(references.get("items"), list) else []
    lines = _code_symbol_header("Code references:", report, "references", references)
    if items:
        lines.append("  matches:")
        for item in items:
            if isinstance(item, dict):
                lines.append(f"    - {item.get('path')}:{item.get('line')}:{item.get('column')} ({item.get('language')}) {item.get('context')}")
    else:
        lines.append("  matches: none")
    return "\n".join(lines)


def format_code_ref_contexts_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    contexts = report.get("contexts") if isinstance(report.get("contexts"), dict) else {}
    items = contexts.get("items") if isinstance(contexts.get("items"), list) else []
    lines = _code_symbol_header("Code reference contexts:", report, "contexts", contexts)
    lines.insert(-1, f"  contextLines: {report.get('contextLines', 3)}")
    lines.insert(-1, f"  maxBytesPerContext: {report.get('maxBytesPerContext', 20000)}")
    if items:
        lines.append("  contexts:")
        for item in items:
            if not isinstance(item, dict):
                continue
            language = item.get("language") or "unknown"
            lines.append(f"    - {item.get('path')}:{item.get('line')}:{item.get('column')} ({language} {item.get('kind')}) range={item.get('start_line')}-{item.get('end_line')} truncated={'yes' if bool(item.get('truncated')) else 'no'}")
            if item.get("matched_line"):
                lines.append(f"      match: {item.get('matched_line')}")
            if item.get("content"):
                lines.append("      content:")
                lines.extend(f"        {line}" for line in str(item.get("content")).splitlines())
    else:
        lines.append("  contexts: none")
    return "\n".join(lines)


def format_code_defs_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    definitions = report.get("definitions") if isinstance(report.get("definitions"), dict) else {}
    items = definitions.get("items") if isinstance(definitions.get("items"), list) else []
    lines = _code_symbol_header("Code definitions:", report, "definitions", definitions)
    _append_errors(lines, report.get("errors"))
    if items:
        lines.append("  matches:")
        for item in items:
            if not isinstance(item, dict):
                continue
            lines.append(f"    - {item.get('path')}:{item.get('line')}:{item.get('end_line')} ({item.get('language')} {item.get('kind')}) {item.get('name')} truncated={'yes' if bool(item.get('truncated')) else 'no'}")
            if item.get("content"):
                lines.append("      content:")
                lines.extend(f"        {line}" for line in str(item.get("content")).splitlines())
    else:
        lines.append("  matches: none")
    return "\n".join(lines)


def _code_symbol_header(title: str, report: dict[str, object], label: str, bucket: dict[str, object]) -> list[str]:
    return [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  symbol: {report.get('symbol') or ''}",
        f"  path: {report.get('path') or '.'}",
        f"  {label}: {bucket.get('shown', 0)}/{bucket.get('total', 0)}",
        f"  truncated: {'yes' if bool(bucket.get('truncated')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]


def _append_errors(lines: list[str], errors: object) -> None:
    if isinstance(errors, list) and errors:
        lines.append("  errors:")
        for error in errors:
            lines.append(f"    - {error}")
