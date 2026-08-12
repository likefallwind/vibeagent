from __future__ import annotations


COMMAND_OUTPUT_EXTRACTION_PROPERTIES: dict[str, dict[str, object]] = {
    "extract_output_contexts": {
        "type": "boolean",
        "description": "When true, extract project file:line references from this command's stdout/stderr and include source contexts. Defaults to false.",
    },
    "extract_output_diagnostics": {
        "type": "boolean",
        "description": "When true, summarize error/warning/failure diagnostic lines from this command's stdout/stderr and include referenced source contexts. Defaults to false.",
    },
    "context_lines": {
        "type": "integer",
        "minimum": 0,
        "maximum": 500,
        "description": "Lines before and after each extracted reference when extract_output_contexts or extract_output_diagnostics is true. Defaults to 5.",
    },
    "max_diagnostics": {
        "type": "integer",
        "minimum": 1,
        "maximum": 200,
        "description": "Maximum diagnostic lines to include when extract_output_diagnostics is true. Defaults to 50.",
    },
    "max_contexts": {
        "type": "integer",
        "minimum": 1,
        "maximum": 100,
        "description": "Maximum extracted contexts for this command. Defaults to 20.",
    },
    "max_bytes_per_context": {
        "type": "integer",
        "minimum": 1000,
        "maximum": 200000,
        "description": "Maximum characters returned per extracted context. Defaults to 20000.",
    },
}


COMMAND_SANDBOX_ESCAPE_PROPERTY: dict[str, dict[str, object]] = {
    "dangerouslyDisableSandbox": {
        "type": "boolean",
        "description": (
            "Request execution outside the command sandbox after sandbox isolation "
            "prevents the command from working. This never bypasses normal permission approval."
        ),
    }
}
