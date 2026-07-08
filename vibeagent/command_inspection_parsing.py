from __future__ import annotations

from .command_types import LocalCommand, make_local_command


def parse_inspection_local_command(trimmed: str) -> LocalCommand | None:
    if trimmed == "/overview" or trimmed.startswith("/overview "):
        return make_local_command("overview", trimmed[10:].strip() or None)
    if trimmed == "/repo-map" or trimmed.startswith("/repo-map "):
        return make_local_command("repo_map", trimmed[9:].strip() or None)
    if trimmed == "/search" or trimmed.startswith("/search "):
        return make_local_command("search", trimmed[7:].strip() or None)
    if trimmed == "/search-contexts" or trimmed.startswith("/search-contexts "):
        return make_local_command("search_contexts", trimmed[16:].strip() or None)
    if trimmed == "/find-files" or trimmed.startswith("/find-files "):
        return make_local_command("find_files", trimmed[12:].strip() or None)
    if trimmed == "/glob" or trimmed.startswith("/glob "):
        return make_local_command("glob", trimmed[6:].strip() or None)
    if trimmed == "/tree" or trimmed.startswith("/tree "):
        return make_local_command("tree", trimmed[6:].strip() or None)
    if trimmed == "/symbols" or trimmed.startswith("/symbols "):
        return make_local_command("symbols", trimmed[9:].strip() or None)
    if trimmed == "/file-info" or trimmed.startswith("/file-info "):
        return make_local_command("file_info", trimmed[11:].strip() or None)
    if trimmed == "/image-info" or trimmed.startswith("/image-info "):
        return make_local_command("image_info", trimmed[12:].strip() or None)
    if trimmed == "/read" or trimmed.startswith("/read "):
        return make_local_command("read", trimmed[6:].strip() or None)
    if trimmed == "/around" or trimmed.startswith("/around "):
        return make_local_command("around", trimmed[8:].strip() or None)
    if trimmed == "/around-many" or trimmed.startswith("/around-many "):
        return make_local_command("around_many", trimmed[13:].strip() or None)
    if trimmed == "/output-contexts" or trimmed.startswith("/output-contexts "):
        return make_local_command("output_contexts", trimmed[16:].strip() or None)
    if trimmed == "/output-diagnostics" or trimmed.startswith("/output-diagnostics "):
        return make_local_command("output_diagnostics", trimmed[19:].strip() or None)
    if trimmed == "/python-traceback" or trimmed.startswith("/python-traceback "):
        return make_local_command("python_traceback", trimmed[17:].strip() or None)
    if trimmed == "/tail" or trimmed.startswith("/tail "):
        return make_local_command("tail", trimmed[6:].strip() or None)
    if trimmed == "/read-files" or trimmed.startswith("/read-files "):
        return make_local_command("read_files", trimmed[12:].strip() or None)
    if trimmed == "/read-ranges" or trimmed.startswith("/read-ranges "):
        return make_local_command("read_ranges", trimmed[13:].strip() or None)
    return None
