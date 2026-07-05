from __future__ import annotations

from typing import Any


FILE_TEXT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
{
        "name": "check_edit_file",
        "description": "Validate one exact text replacement in an existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
            "additionalProperties": False,
        },
    },
{
        "name": "edit_file",
        "description": "Replace one exact text block in an existing project file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_multi_edit_file",
        "description": "Validate multiple exact text replacements against one existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "edits": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "old": {"type": "string"},
                            "new": {"type": "string"},
                        },
                        "required": ["old", "new"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["path", "edits"],
            "additionalProperties": False,
        },
    },
{
        "name": "multi_edit_file",
        "description": "Apply multiple exact text replacements to one existing project file atomically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "edits": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "old": {"type": "string"},
                            "new": {"type": "string"},
                        },
                        "required": ["old", "new"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["path", "edits"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_replace_lines",
        "description": "Validate an inclusive 1-based line range replacement in one existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
                "content": {
                    "type": "string",
                    "description": "Replacement text for the selected lines. Use an empty string to delete the range.",
                },
            },
            "required": ["path", "start_line", "end_line", "content"],
            "additionalProperties": False,
        },
    },
{
        "name": "replace_lines",
        "description": "Replace an inclusive 1-based line range in one existing project file. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
                "content": {
                    "type": "string",
                    "description": "Replacement text for the selected lines. Use an empty string to delete the range.",
                },
            },
            "required": ["path", "start_line", "end_line", "content"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_insert_lines",
        "description": "Validate inserting text before a 1-based line in one existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "line": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "1-based line before which to insert. Use file line count + 1 to append.",
                },
                "content": {"type": "string", "description": "Text to insert."},
            },
            "required": ["path", "line", "content"],
            "additionalProperties": False,
        },
    },
{
        "name": "insert_lines",
        "description": "Insert text before a 1-based line in one existing project file. Use line_count + 1 to append. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "line": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "1-based line before which to insert. Use file line count + 1 to append.",
                },
                "content": {"type": "string", "description": "Text to insert."},
            },
            "required": ["path", "line", "content"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_append_file",
        "description": "Validate appending exact UTF-8 text to one existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string", "description": "Text to append exactly as provided."},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
{
        "name": "append_file",
        "description": "Append exact UTF-8 text to one existing project file. Does not add an implicit newline. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string", "description": "Exact text to append."},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_regex_replace",
        "description": "Preview a Python regular expression replacement in one existing UTF-8 project file without writing changes. Returns replacement count and diff.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string", "description": "Python regular expression pattern. Must not be empty."},
                "replacement": {"type": "string", "description": "Python regex replacement text, including backreferences if needed."},
                "count": {"type": "integer", "minimum": 0, "description": "Maximum replacements to preview. Use 0 for all matches."},
                "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive. Defaults to true."},
                "multiline": {"type": "boolean", "description": "Whether ^ and $ match line boundaries. Defaults to false."},
                "max_replacements": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
            "required": ["path", "pattern", "replacement"],
            "additionalProperties": False,
        },
    },
{
        "name": "regex_replace",
        "description": "Apply a Python regular expression replacement to one existing UTF-8 project file after bounding the replacement count. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string", "description": "Python regular expression pattern. Must not be empty."},
                "replacement": {"type": "string", "description": "Python regex replacement text, including backreferences if needed."},
                "count": {"type": "integer", "minimum": 0, "description": "Maximum replacements to apply. Use 0 for all matches."},
                "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive. Defaults to true."},
                "multiline": {"type": "boolean", "description": "Whether ^ and $ match line boundaries. Defaults to false."},
                "max_replacements": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
            "required": ["path", "pattern", "replacement"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_patch",
        "description": "Validate one unified diff patch against an existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "patch": {
                    "type": "string",
                    "description": "Unified diff text with @@ hunk headers. The file path is provided separately.",
                },
            },
            "required": ["path", "patch"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_patches",
        "description": "Validate a multi-file unified diff without writing changes. The diff may modify existing text files, create new text files, or delete text files. Returns the combined diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patch": {
                    "type": "string",
                    "description": "Unified diff text with ---/+++ file headers and @@ hunk headers.",
                },
            },
            "required": ["patch"],
            "additionalProperties": False,
        },
    },
{
        "name": "patch_file",
        "description": "Apply one or more unified diff hunks to an existing project file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "patch": {
                    "type": "string",
                    "description": "Unified diff text with @@ hunk headers. The file path is provided separately.",
                },
            },
            "required": ["path", "patch"],
            "additionalProperties": False,
        },
    },
{
        "name": "patch_files",
        "description": "Apply a multi-file unified diff atomically. The diff may modify existing text files, create new text files, or delete text files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patch": {
                    "type": "string",
                    "description": "Unified diff text with ---/+++ file headers and @@ hunk headers.",
                },
            },
            "required": ["patch"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_write_file",
        "description": "Validate creating or replacing one UTF-8 text file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
{
        "name": "write_file",
        "description": "Create or replace a UTF-8 text file under the project directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_write_files",
        "description": "Validate creating or replacing up to 20 UTF-8 text files without writing changes. Returns per-file diffs that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                        "additionalProperties": False,
                    },
                    "description": "Files to create or replace.",
                }
            },
            "required": ["files"],
            "additionalProperties": False,
        },
    },
{
        "name": "write_files",
        "description": "Create or replace up to 20 UTF-8 text files under the project directory in one atomic operation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                        "additionalProperties": False,
                    },
                    "description": "Files to create or replace.",
                }
            },
            "required": ["files"],
            "additionalProperties": False,
        },
    },
]
