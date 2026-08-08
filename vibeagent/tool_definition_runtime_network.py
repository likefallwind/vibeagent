from __future__ import annotations

from typing import Any


RUNTIME_NETWORK_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "port_check",
        "description": "Check whether a TCP host:port is reachable without running a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "host": {"type": "string", "description": "Host to connect to. Defaults to 127.0.0.1."},
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 10000,
                    "description": "Optional connect timeout in milliseconds. Defaults to 1000.",
                },
            },
            "required": ["port"],
            "additionalProperties": False,
        },
    },
    {
        "name": "http_check",
        "description": "Check a local or private HTTP(S) development URL status, final URL, and optional body match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Local or private HTTP or HTTPS URL to request."},
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 10000,
                    "description": "Optional request timeout in milliseconds. Defaults to 2000.",
                },
                "max_body_chars": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50000,
                    "description": "Maximum response body characters to return. Defaults to 2000; use 0 for status-only checks.",
                },
                "contains": {
                    "type": "string",
                    "description": "Optional literal text or regex pattern to search for in the response body.",
                },
                "regex": {
                    "type": "boolean",
                    "description": "Treat contains as a regular expression when true. Defaults to false.",
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        },
    },
    {
        "name": "http_fetch",
        "description": "Fetch a local or private HTTP(S) development URL and return bounded response metadata plus body text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Local or private HTTP or HTTPS URL to request."},
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 10000,
                    "description": "Optional request timeout in milliseconds. Defaults to 5000.",
                },
                "max_body_chars": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100000,
                    "description": "Maximum response body characters to return. Defaults to 12000.",
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        },
    },
    {
        "name": "web_fetch",
        "description": "Fetch readable text from a public HTTP(S) technical document. Requires approval and rejects local/private targets and unsafe redirects.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Public HTTP or HTTPS document URL."},
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 10000,
                    "description": "Optional request timeout in milliseconds. Defaults to 10000.",
                },
                "max_text_chars": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100000,
                    "description": "Maximum readable text characters to return. Defaults to 20000.",
                },
                "prompt": {
                    "type": "string",
                    "description": "Optional extraction or question prompt to carry alongside the fetched text for the next model step.",
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        },
    },
    {
        "name": "WebFetch",
        "description": "Claude-compatible alias for fetching readable text from a public HTTP(S) technical document after approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Public HTTP or HTTPS document URL."},
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 10000,
                    "description": "Optional request timeout in milliseconds. Defaults to 10000.",
                },
                "max_text_chars": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100000,
                    "description": "Maximum readable text characters to return. Defaults to 20000.",
                },
                "prompt": {"type": "string", "description": "Optional extraction or question prompt."},
            },
            "required": ["url"],
            "additionalProperties": False,
        },
    },
    {
        "name": "web_search",
        "description": "Search the public web through DuckDuckGo and return bounded result titles, URLs, and snippets. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query, limited to 500 characters."},
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 10000,
                    "description": "Optional request timeout in milliseconds. Defaults to 10000.",
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum number of results to return. Defaults to 5.",
                },
                "allowed_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 20,
                    "description": "Optional domains to include, including their subdomains.",
                },
                "blocked_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 20,
                    "description": "Optional domains to exclude, including their subdomains.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "WebSearch",
        "description": "Claude-compatible alias for searching the public web after approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query, limited to 500 characters."},
                "allowed_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 20,
                },
                "blocked_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 20,
                },
                "timeout_ms": {"type": "integer", "minimum": 100, "maximum": 10000},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
]
