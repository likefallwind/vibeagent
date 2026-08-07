from __future__ import annotations


def normalized_approval_target_tokens(value: object) -> set[str]:
    text = str(value or "").strip()
    if not text:
        return set()
    if should_preserve_approval_target(text):
        return {text}
    tokens: set[str] = set()
    candidates = [text]
    candidates.extend(part.strip() for part in text.split(","))
    split_candidates = list(candidates)
    for candidate in split_candidates:
        if should_preserve_approval_target(candidate):
            continue
        if " -> " in candidate and "," not in candidate and not _looks_like_transfer_target(candidate):
            candidates.extend(part.strip() for part in candidate.split(" -> "))
        if " " in candidate:
            candidates.append(candidate.split(" ", 1)[0].strip())
        if ":" in candidate and "://" not in candidate:
            candidates.append(candidate.split(":", 1)[0].strip())
    for candidate in candidates:
        normalized = candidate.strip()
        if normalized:
            tokens.add(normalized)
    return tokens


def should_preserve_approval_target(text: str) -> bool:
    return (
        "(cwd:" in text
        or _looks_like_path_pointer_target(text)
        or _looks_like_path_line_target(text)
        or _looks_like_symbol_target(text)
        or _looks_like_operation_count_target(text)
        or _looks_like_char_count_target(text)
        or _looks_like_transfer_target(text)
        or _looks_like_mcp_arguments_target(text)
        or _looks_like_git_switch_create_target(text)
        or _looks_like_comma_list_target(text)
    )


def _looks_like_path_pointer_target(text: str) -> bool:
    parts = text.split(" ", 1)
    return len(parts) == 2 and parts[1].startswith("/")


def _looks_like_path_line_target(text: str) -> bool:
    prefix, separator, suffix = text.rpartition(":")
    if not separator or not prefix or not suffix:
        return False
    if "-" in suffix:
        start, end = suffix.split("-", 1)
        return bool(start.isdigit() and end.isdigit())
    return suffix.isdigit()


def _looks_like_symbol_target(text: str) -> bool:
    if " in " not in text:
        return False
    symbol_part, _, path_part = text.rpartition(" in ")
    if not symbol_part.strip() or not path_part.strip():
        return False
    if " -> " in symbol_part:
        old_name, new_name = symbol_part.split(" -> ", 1)
        return bool(old_name.strip() and new_name.strip())
    return True


def _looks_like_operation_count_target(text: str) -> bool:
    return _looks_like_count_target(text, "operations")


def _looks_like_char_count_target(text: str) -> bool:
    return _looks_like_count_target(text, "chars")


def _looks_like_count_target(text: str, label: str) -> bool:
    prefix, separator, suffix = text.rpartition(" (")
    suffix_text = f" {label})"
    if not separator or not prefix.strip() or not suffix.endswith(suffix_text):
        return False
    count_text = suffix.removesuffix(suffix_text)
    return count_text.isdigit()


def _looks_like_transfer_target(text: str) -> bool:
    if "," in text:
        return False
    source, separator, destination = text.partition(" -> ")
    return bool(separator and source.strip() and destination.strip())


def _looks_like_comma_list_target(text: str) -> bool:
    return "," in text and all(part.strip() for part in text.split(","))


def _looks_like_mcp_arguments_target(text: str) -> bool:
    tool, separator, arguments = text.partition(" arguments=")
    return bool(separator and "/" in tool and tool.strip() and arguments.strip())


def _looks_like_git_switch_create_target(text: str) -> bool:
    return text.endswith(" (create)") and bool(text.removesuffix(" (create)").strip())
