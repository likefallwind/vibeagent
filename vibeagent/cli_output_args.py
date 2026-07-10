from __future__ import annotations

import argparse


OUTPUT_FORMATS = ("text", "json", "stream-json")


def add_output_arguments(parser: argparse.ArgumentParser) -> None:
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="Print a single JSON result for one-shot or local command output.")
    output.add_argument(
        "--output-format",
        choices=OUTPUT_FORMATS,
        help="Output format for one-shot tasks; stream-json emits newline-delimited session events and a final result.",
    )


def normalize_output_arguments(args: argparse.Namespace) -> argparse.Namespace:
    requested = args.output_format or ("json" if args.json else "text")
    args.output_format = requested
    args.json = requested in {"json", "stream-json"}
    return args


__all__ = ["OUTPUT_FORMATS", "add_output_arguments", "normalize_output_arguments"]
