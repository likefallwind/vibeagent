from __future__ import annotations

from typing import Any

from .action_parsing_file_edit_fields import parse_regex_replace, parse_string_field
from .types import CheckPatchAction, CheckPatchesAction, CheckRegexReplaceAction, PatchFileAction, PatchFilesAction, RegexReplaceAction


FILE_PATCH_ACTION_TYPES = {
    "check_regex_replace",
    "regex_replace",
    "check_patch",
    "check_patches",
    "patch_file",
    "patch_files",
}


def parse_file_patch_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in FILE_PATCH_ACTION_TYPES:
        return None

    if action_type == "check_regex_replace":
        path, pattern, replacement, count, case_sensitive, multiline, max_replacements = parse_regex_replace(
            value,
            raw,
            "check_regex_replace",
        )
        return CheckRegexReplaceAction(
            type="check_regex_replace",
            path=path,
            pattern=pattern,
            replacement=replacement,
            count=count,
            case_sensitive=case_sensitive,
            multiline=multiline,
            max_replacements=max_replacements,
        )

    if action_type == "regex_replace":
        path, pattern, replacement, count, case_sensitive, multiline, max_replacements = parse_regex_replace(
            value,
            raw,
            "regex_replace",
        )
        return RegexReplaceAction(
            type="regex_replace",
            path=path,
            pattern=pattern,
            replacement=replacement,
            count=count,
            case_sensitive=case_sensitive,
            multiline=multiline,
            max_replacements=max_replacements,
        )

    if action_type == "check_patch":
        path = parse_string_field(value.get("path"), raw, "check_patch action requires a string path.")
        patch = parse_string_field(value.get("patch"), raw, "check_patch action requires string patch.")
        return CheckPatchAction(type="check_patch", path=path, patch=patch)

    if action_type == "check_patches":
        patch = parse_string_field(value.get("patch"), raw, "check_patches action requires string patch.")
        return CheckPatchesAction(type="check_patches", patch=patch)

    if action_type == "patch_file":
        path = parse_string_field(value.get("path"), raw, "patch_file action requires a string path.")
        patch = parse_string_field(value.get("patch"), raw, "patch_file action requires string patch.")
        return PatchFileAction(type="patch_file", path=path, patch=patch)

    if action_type == "patch_files":
        patch = parse_string_field(value.get("patch"), raw, "patch_files action requires string patch.")
        return PatchFilesAction(type="patch_files", patch=patch)

    raise AssertionError(f"Unhandled file patch action type: {action_type!r}")
