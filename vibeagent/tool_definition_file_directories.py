from __future__ import annotations

from typing import Any


FILE_DIRECTORY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
