from __future__ import annotations

from typing import Any


JSON_EDITING_TOOL_DEFINITIONS: list[dict[str, Any]] = [
{
        "name": "check_json_set",
        "description": "Preview setting one value in an existing project JSON file using a JSON Pointer without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative JSON file path."},
                "pointer": {"type": "string", "description": "JSON Pointer to set, such as /scripts/dev or /compilerOptions/strict."},
                "value": {
                    "description": "JSON value to write at the pointer.",
                    "type": ["string", "number", "integer", "boolean", "object", "array", "null"],
                },
                "create_missing": {
                    "type": "boolean",
                    "description": "Create missing object keys along the pointer when true. Defaults to false.",
                },
            },
            "required": ["path", "pointer", "value"],
            "additionalProperties": False,
        },
    },
{
        "name": "json_set",
        "description": "Set one value in an existing project JSON file using a JSON Pointer after approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative JSON file path."},
                "pointer": {"type": "string", "description": "JSON Pointer to set, such as /scripts/dev or /compilerOptions/strict."},
                "value": {
                    "description": "JSON value to write at the pointer.",
                    "type": ["string", "number", "integer", "boolean", "object", "array", "null"],
                },
                "create_missing": {
                    "type": "boolean",
                    "description": "Create missing object keys along the pointer when true. Defaults to false.",
                },
            },
            "required": ["path", "pointer", "value"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_json_remove",
        "description": "Preview removing one object key or array item from an existing project JSON file using a JSON Pointer without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative JSON file path."},
                "pointer": {"type": "string", "description": "JSON Pointer to remove, such as /scripts/dev or /keywords/0."},
            },
            "required": ["path", "pointer"],
            "additionalProperties": False,
        },
    },
{
        "name": "json_remove",
        "description": "Remove one object key or array item from an existing project JSON file using a JSON Pointer after approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative JSON file path."},
                "pointer": {"type": "string", "description": "JSON Pointer to remove, such as /scripts/dev or /keywords/0."},
            },
            "required": ["path", "pointer"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_json_patch",
        "description": "Preview applying multiple JSON Patch operations to one existing project JSON file without changing files. Supports add, replace, and remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative JSON file path."},
                "operations": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 50,
                    "items": {
                        "type": "object",
                        "oneOf": [
                            {
                                "properties": {
                                    "op": {"type": "string", "enum": ["add", "replace"]},
                                    "path": {"type": "string", "description": "JSON Pointer path for this operation."},
                                    "value": {
                                        "description": "JSON value for add or replace operations.",
                                        "type": ["string", "number", "integer", "boolean", "object", "array", "null"],
                                    },
                                },
                                "required": ["op", "path", "value"],
                                "additionalProperties": False,
                            },
                            {
                                "properties": {
                                    "op": {"type": "string", "enum": ["remove"]},
                                    "path": {"type": "string", "description": "JSON Pointer path for this operation."},
                                },
                                "required": ["op", "path"],
                                "additionalProperties": False,
                            },
                        ],
                    },
                },
            },
            "required": ["path", "operations"],
            "additionalProperties": False,
        },
    },
{
        "name": "json_patch",
        "description": "Apply multiple JSON Patch operations to one existing project JSON file after approval. Supports add, replace, and remove, and validates all operations before writing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative JSON file path."},
                "operations": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 50,
                    "items": {
                        "type": "object",
                        "oneOf": [
                            {
                                "properties": {
                                    "op": {"type": "string", "enum": ["add", "replace"]},
                                    "path": {"type": "string", "description": "JSON Pointer path for this operation."},
                                    "value": {
                                        "description": "JSON value for add or replace operations.",
                                        "type": ["string", "number", "integer", "boolean", "object", "array", "null"],
                                    },
                                },
                                "required": ["op", "path", "value"],
                                "additionalProperties": False,
                            },
                            {
                                "properties": {
                                    "op": {"type": "string", "enum": ["remove"]},
                                    "path": {"type": "string", "description": "JSON Pointer path for this operation."},
                                },
                                "required": ["op", "path"],
                                "additionalProperties": False,
                            },
                        ],
                    },
                },
            },
            "required": ["path", "operations"],
            "additionalProperties": False,
        },
    },
]
