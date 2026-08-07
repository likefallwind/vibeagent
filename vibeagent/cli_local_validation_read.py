from __future__ import annotations

import argparse


def validate_read_discovery_option_dependencies(args: argparse.Namespace) -> str | None:
    search_selected = args.search is not None or args.search_contexts is not None
    if args.search_path and not search_selected:
        return "--search-path can only be used with --search or --search-contexts."
    if args.search_max_matches is not None and not search_selected:
        return "--search-max-matches can only be used with --search or --search-contexts."
    if args.search_regex and not search_selected:
        return "--search-regex can only be used with --search or --search-contexts."
    if args.search_ignore_case and not search_selected:
        return "--search-ignore-case can only be used with --search or --search-contexts."
    if args.search_context_lines is not None and not search_selected:
        return "--search-context-lines can only be used with --search or --search-contexts."
    if args.search_context_max_bytes is not None and args.search_contexts is None:
        return "--search-context-max-bytes can only be used with --search-contexts."
    if args.find_files_path and args.find_files is None:
        return "--find-files-path can only be used with --find-files."
    if args.find_files_max_matches is not None and args.find_files is None:
        return "--find-files-max-matches can only be used with --find-files."
    if args.find_files_regex and args.find_files is None:
        return "--find-files-regex can only be used with --find-files."
    if args.find_files_case_sensitive and args.find_files is None:
        return "--find-files-case-sensitive can only be used with --find-files."
    if args.find_files_include_dirs and args.find_files is None:
        return "--find-files-include-dirs can only be used with --find-files."
    if args.repo_map_max_depth is not None and args.repo_map is None:
        return "--repo-map-max-depth can only be used with --repo-map."
    if args.repo_map_max_files is not None and args.repo_map is None:
        return "--repo-map-max-files can only be used with --repo-map."
    if args.repo_map_max_symbols is not None and args.repo_map is None:
        return "--repo-map-max-symbols can only be used with --repo-map."
    if args.glob_max_matches is not None and args.glob is None:
        return "--glob-max-matches can only be used with --glob."
    if args.glob_include_dirs and args.glob is None:
        return "--glob-include-dirs can only be used with --glob."
    if args.tree_max_depth is not None and args.tree is None:
        return "--tree-max-depth can only be used with --tree."
    if args.tree_max_entries is not None and args.tree is None:
        return "--tree-max-entries can only be used with --tree."
    if args.read_lines and args.read is None:
        return "--read-lines can only be used with --read."
    if args.read_max_bytes is not None and args.read is None:
        return "--read-max-bytes can only be used with --read."
    if args.read_line_numbers and args.read is None:
        return "--read-line-numbers can only be used with --read."
    if args.read_files_max_bytes is not None and args.read_files is None:
        return "--read-files-max-bytes can only be used with --read-files."
    if args.read_files_line_numbers and args.read_files is None:
        return "--read-files-line-numbers can only be used with --read-files."
    if args.read_ranges_max_bytes is not None and args.read_ranges is None:
        return "--read-ranges-max-bytes can only be used with --read-ranges."
    if args.around_lines != 20 and args.around is None:
        return "--around-lines can only be used with --around."
    if args.around_max_bytes is not None and args.around is None:
        return "--around-max-bytes can only be used with --around."
    if args.around_many_max_bytes is not None and args.around_many is None:
        return "--around-many-max-bytes can only be used with --around-many."
    if args.output_context_lines != 5 and args.output_contexts is None:
        return "--output-context-lines can only be used with --output-contexts."
    if args.output_context_max != 20 and args.output_contexts is None:
        return "--output-context-max can only be used with --output-contexts."
    if args.output_context_max_bytes != 20_000 and args.output_contexts is None:
        return "--output-context-max-bytes can only be used with --output-contexts."
    output_diagnostic_analysis = args.output_diagnostics is not None or args.python_traceback is not None
    if args.output_diagnostic_lines != 2 and not output_diagnostic_analysis:
        return "--output-diagnostic-lines can only be used with --output-diagnostics or --python-traceback."
    if args.output_diagnostic_max != 50 and not output_diagnostic_analysis:
        return "--output-diagnostic-max can only be used with --output-diagnostics or --python-traceback."
    if args.output_diagnostic_context_max != 20 and not output_diagnostic_analysis:
        return "--output-diagnostic-context-max can only be used with --output-diagnostics or --python-traceback."
    if args.output_diagnostic_context_max_bytes != 20_000 and not output_diagnostic_analysis:
        return "--output-diagnostic-context-max-bytes can only be used with --output-diagnostics or --python-traceback."
    return None


def validate_code_intel_option_dependencies(args: argparse.Namespace) -> str | None:
    if args.symbols_max is not None and args.symbols is None:
        return "--symbols-max can only be used with --symbols."
    python_symbol_lookup_selected = (
        args.python_defs is not None
        or args.python_refs is not None
        or args.python_ref_contexts is not None
        or args.python_calls is not None
    )
    if args.python_max_matches is not None and not python_symbol_lookup_selected:
        return "--python-max-matches can only be used with --python-defs, --python-refs, --python-ref-contexts, or --python-calls."
    if args.python_def_max_lines is not None and args.python_defs is None:
        return "--python-def-max-lines can only be used with --python-defs."
    if args.python_context_lines is not None and args.python_ref_contexts is None:
        return "--python-context-lines can only be used with --python-ref-contexts."
    if args.python_context_max_bytes is not None and args.python_ref_contexts is None:
        return "--python-context-max-bytes can only be used with --python-ref-contexts."
    if args.python_deps_max_files is not None and args.python_deps is None:
        return "--python-deps-max-files can only be used with --python-deps."
    if args.python_deps_max_imports is not None and args.python_deps is None:
        return "--python-deps-max-imports can only be used with --python-deps."
    if args.python_call_graph_max_files is not None and args.python_call_graph is None:
        return "--python-call-graph-max-files can only be used with --python-call-graph."
    if args.python_call_graph_max_edges is not None and args.python_call_graph is None:
        return "--python-call-graph-max-edges can only be used with --python-call-graph."
    code_symbol_lookup_selected = (
        args.code_refs is not None
        or args.code_ref_contexts is not None
        or args.code_defs is not None
    )
    if args.code_max_matches is not None and not code_symbol_lookup_selected:
        return "--code-max-matches can only be used with --code-refs, --code-ref-contexts, or --code-defs."
    if args.code_def_max_lines is not None and args.code_defs is None:
        return "--code-def-max-lines can only be used with --code-defs."
    if args.code_context_lines is not None and args.code_ref_contexts is None:
        return "--code-context-lines can only be used with --code-ref-contexts."
    if args.code_context_max_bytes is not None and args.code_ref_contexts is None:
        return "--code-context-max-bytes can only be used with --code-ref-contexts."
    return None
