from __future__ import annotations

from typing import Any


FILE_EDITING_TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
{
        "name": "check_delete_file",
        "description": "Validate deleting one existing UTF-8 text project file without removing it. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
{
        "name": "delete_file",
        "description": "Delete one existing project file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_delete_files",
        "description": "Validate deleting explicit existing UTF-8 text project files without removing them. Returns the combined diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                    "description": "Explicit project-relative file paths to delete. Globs are not expanded.",
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
{
        "name": "delete_files",
        "description": "Delete explicit existing project files after approval. All files are validated before any file is removed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                    "description": "Explicit project-relative file paths to delete. Globs are not expanded.",
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_move_file",
        "description": "Validate moving or renaming one existing project file to a new project-relative path without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
{
        "name": "move_file",
        "description": "Move or rename one existing project file to a new project-relative path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_move_files",
        "description": "Validate moving or renaming explicit existing project files without changing files. All transfers are validated together.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
{
        "name": "move_files",
        "description": "Move or rename explicit existing project files after approval. All transfers are validated before any file is moved.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_copy_file",
        "description": "Validate copying one existing project file to a new project-relative path without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
{
        "name": "copy_file",
        "description": "Copy one existing project file to a new project-relative path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_copy_files",
        "description": "Validate copying explicit existing project files to new project-relative paths without changing files. All transfers are validated together.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
{
        "name": "copy_files",
        "description": "Copy explicit existing project files to new project-relative paths after approval. All transfers are validated before any file is copied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_move_dir",
        "description": "Validate moving or renaming one existing project directory to a new project-relative path without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
{
        "name": "move_dir",
        "description": "Move or rename one existing project directory to a new project-relative path without overwriting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_move_dirs",
        "description": "Validate moving or renaming one or more existing project directories to new project-relative paths without changing files. Rejects overlapping sources or destinations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
{
        "name": "move_dirs",
        "description": "Move or rename one or more existing project directories to new project-relative paths without overwriting after validating the whole batch. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_copy_dir",
        "description": "Validate copying one existing project directory tree to a new project-relative path without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_copy_dirs",
        "description": "Validate copying one or more existing project directory trees to new project-relative paths without changing files. Rejects symbolic links, very large directories, protected paths, and overlapping destinations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
{
        "name": "copy_dir",
        "description": "Copy one existing project directory to a new project-relative path without overwriting. Refuses symbolic links, very large directories, and protected paths.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
{
        "name": "copy_dirs",
        "description": "Copy one or more existing project directories to new project-relative paths without overwriting after validating the whole batch. Refuses symbolic links, very large directories, and protected paths. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_create_dir",
        "description": "Validate creating one project-relative directory, including missing parent directories, without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_create_dirs",
        "description": "Validate creating one or more project-relative directories, including missing parent directories, without changing files. Rejects duplicate targets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
{
        "name": "create_dir",
        "description": "Create one project-relative directory, including missing parent directories. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
{
        "name": "create_dirs",
        "description": "Create one or more project-relative directories, including missing parent directories. Validates all targets before creating any directory. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_delete_empty_dir",
        "description": "Validate deleting one existing empty project-relative directory without removing it.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_delete_empty_dirs",
        "description": "Validate deleting one or more existing empty project-relative directories without removing them. Parent directories may be included when their listed child directories are also deleted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
{
        "name": "delete_empty_dir",
        "description": "Delete one existing empty project-relative directory. Does not delete non-empty directories. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
{
        "name": "delete_empty_dirs",
        "description": "Delete one or more existing empty project-relative directories after validating all targets. Does not delete non-empty directories. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_set_executable",
        "description": "Validate setting or clearing executable permission bits on one existing project file without changing mode bits.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "executable": {
                    "type": "boolean",
                    "description": "True to add executable bits, false to remove them. Defaults to true.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
{
        "name": "set_executable",
        "description": "Set or clear executable permission bits on one existing project file. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "executable": {
                    "type": "boolean",
                    "description": "True to add executable bits, false to remove them. Defaults to true.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
]
