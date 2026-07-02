from __future__ import annotations

from typing import Any


CODE_INTEL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
{
        "name": "python_dependencies",
        "description": "Inspect Python imports without executing code, classifying local project modules versus external modules.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python file count to inspect. Defaults to 100.",
                },
                "max_imports": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum import entries to return across files. Defaults to 500.",
                },
            },
            "additionalProperties": False,
        },
    },
{
        "name": "code_dependencies",
        "description": "Inspect imports, includes, and use statements in JavaScript, TypeScript, Go, Rust, Java, Kotlin, C, and C++ files without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum source file count to inspect. Defaults to 100.",
                },
                "max_imports": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum import/include/use entries to return across files. Defaults to 500.",
                },
            },
            "additionalProperties": False,
        },
    },
{
        "name": "code_references",
        "description": "Find bounded references to one symbol or literal in JavaScript, TypeScript, Go, Rust, Java, Kotlin, C, and C++ source files without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol or single-line literal to search for."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum reference count to return. Defaults to 200.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
{
        "name": "code_reference_contexts",
        "description": "Find non-Python source references and return structured line-centered context snippets for each match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol or single-line literal to search for."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum context count to return. Defaults to 50.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "description": "Number of surrounding lines to include around each reference. Defaults to 3.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per context snippet. Defaults to 20000.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
{
        "name": "code_definitions",
        "description": "Find non-Python source definitions by exact symbol name and return focused source excerpts without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Exact symbol name to inspect."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum definition count to return. Defaults to 50.",
                },
                "max_lines": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum source lines to return per definition. Defaults to 80.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
{
        "name": "code_rename_preview",
        "description": "Preview a bounded non-Python source symbol or literal rename using lexical reference matching without writing changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol or single-line literal to rename."},
                "new_name": {"type": "string", "description": "Replacement symbol or single-line literal."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum source file count to inspect. Defaults to 100.",
                },
                "max_replacements": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum replacement count to include in diffs. Defaults to 500.",
                },
            },
            "required": ["symbol", "new_name"],
            "additionalProperties": False,
        },
    },
{
        "name": "code_rename",
        "description": "Apply a bounded non-Python source symbol or literal rename using lexical reference matching.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol or single-line literal to rename."},
                "new_name": {"type": "string", "description": "Replacement symbol or single-line literal."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum source file count to inspect. Defaults to 100.",
                },
                "max_replacements": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum replacement count to apply. Defaults to 2000.",
                },
            },
            "required": ["symbol", "new_name"],
            "additionalProperties": False,
        },
    },
{
        "name": "python_definitions",
        "description": "Find Python class/function definitions and return focused source excerpts without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Python identifier or dotted identifier to inspect, such as run_agent or Runner.run.",
                },
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum definition count to return. Defaults to 50.",
                },
                "max_lines": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum source lines to include for each definition. Defaults to 120.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_replace_python_definition",
        "description": "Validate replacing exactly one Python class/function definition by symbol without changing files. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Python definition name or dotted qualified name, such as run_agent or Runner.run.",
                },
                "content": {
                    "type": "string",
                    "description": "Replacement source text for the full definition, with indentation appropriate for its location.",
                },
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
            },
            "required": ["symbol", "content"],
            "additionalProperties": False,
        },
    },
{
        "name": "replace_python_definition",
        "description": "Replace exactly one Python class/function definition by symbol after validating the resulting file parses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Python definition name or dotted qualified name, such as run_agent or Runner.run.",
                },
                "content": {
                    "type": "string",
                    "description": "Replacement source text for the full definition, with indentation appropriate for its location.",
                },
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
            },
            "required": ["symbol", "content"],
            "additionalProperties": False,
        },
    },
{
        "name": "python_calls",
        "description": "Find Python call sites for a function, method, or dotted callable name without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Python callable name to find, such as run_agent, self.run, or client.complete.",
                },
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum call site count to return. Defaults to 200.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
{
        "name": "python_call_graph",
        "description": "Inspect Python caller-to-callee edges in a file or directory without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python file count to inspect. Defaults to 100.",
                },
                "max_edges": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum call graph edge count to return. Defaults to 500.",
                },
            },
            "additionalProperties": False,
        },
    },
{
        "name": "python_references",
        "description": "Find Python definitions, imports, and AST references for one identifier without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Python identifier to find, such as Client or run_agent."},
                "path": {"type": "string", "description": "Optional project-relative file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum reference count to return. Defaults to 200.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
{
        "name": "python_reference_contexts",
        "description": "Find Python definitions, imports, and AST references, then return structured line-centered context snippets for each match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Python identifier to find, such as Client or run_agent."},
                "path": {"type": "string", "description": "Optional project-relative file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum context count to return. Defaults to 50.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "description": "Number of surrounding lines to include around each reference. Defaults to 3.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per context snippet. Defaults to 20000.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
{
        "name": "python_rename_preview",
        "description": "Preview an AST-guided Python identifier rename across files without writing changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Simple Python identifier to rename."},
                "new_name": {"type": "string", "description": "Replacement simple Python identifier."},
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python file count to inspect. Defaults to 100.",
                },
                "max_replacements": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum replacement count to include in diffs. Defaults to 500.",
                },
            },
            "required": ["symbol", "new_name"],
            "additionalProperties": False,
        },
    },
{
        "name": "python_rename",
        "description": "Apply an AST-guided Python identifier rename across files after validating updated files parse.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Simple Python identifier to rename."},
                "new_name": {"type": "string", "description": "Replacement simple Python identifier."},
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python file count to inspect. Defaults to 100.",
                },
                "max_replacements": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum replacement count to apply. Defaults to 2000.",
                },
            },
            "required": ["symbol", "new_name"],
            "additionalProperties": False,
        },
    },
{
        "name": "search",
        "description": "Search project text for an exact query string or regex, optionally under one path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path": {"type": "string", "description": "Optional project-relative file or directory to search."},
                "regex": {"type": "boolean", "description": "Treat query as a regular expression."},
                "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive. Defaults to true."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum match count to return. Defaults to 80.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 5,
                    "description": "Number of surrounding lines to include around each match. Defaults to 0.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
{
        "name": "search_contexts",
        "description": "Search project text and return structured line-centered context snippets for each match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path": {"type": "string", "description": "Optional project-relative file or directory to search."},
                "regex": {"type": "boolean", "description": "Treat query as a regular expression."},
                "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive. Defaults to true."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum context count to return. Defaults to 20.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "description": "Number of surrounding lines to include around each match. Defaults to 3.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per context snippet. Defaults to 20000.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
{
        "name": "find_files",
        "description": "Find project file paths by substring or regex without reading file contents. Use this when you know part of a filename or path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Filename or project-relative path fragment to match."},
                "path": {"type": "string", "description": "Optional project-relative file or directory scope to search."},
                "regex": {"type": "boolean", "description": "Treat query as a regular expression. Defaults to false."},
                "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive. Defaults to false."},
                "include_dirs": {"type": "boolean", "description": "Whether directory matches should be returned with trailing slashes. Defaults to false."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum path count to return. Defaults to 100.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
{
        "name": "glob",
        "description": "Find project files by relative glob pattern, such as **/*.py or tests/test_*.py. Can include directory matches when requested.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum match count to return. Defaults to 200.",
                },
                "include_dirs": {
                    "type": "boolean",
                    "description": "Whether directory matches should be returned with trailing slashes. Defaults to false.",
                },
            },
            "required": ["pattern"],
            "additionalProperties": False,
        },
    },
]
