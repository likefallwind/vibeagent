from __future__ import annotations

from .command_types import LocalCommand, make_local_command


def parse_file_edit_local_command(trimmed: str) -> LocalCommand | None:
    if trimmed == "/check-replace-lines" or trimmed.startswith("/check-replace-lines "):
        return make_local_command("check_replace_lines", trimmed[21:].strip() or None)
    if trimmed == "/replace-lines" or trimmed.startswith("/replace-lines "):
        return make_local_command("replace_lines", trimmed[15:].strip() or None)
    if trimmed == "/check-insert-lines" or trimmed.startswith("/check-insert-lines "):
        return make_local_command("check_insert_lines", trimmed[20:].strip() or None)
    if trimmed == "/insert-lines" or trimmed.startswith("/insert-lines "):
        return make_local_command("insert_lines", trimmed[14:].strip() or None)
    if trimmed == "/check-append" or trimmed.startswith("/check-append "):
        return make_local_command("check_append_file", trimmed[14:].strip() or None)
    if trimmed == "/append" or trimmed.startswith("/append "):
        return make_local_command("append_file", trimmed[8:].strip() or None)
    if trimmed == "/check-write" or trimmed.startswith("/check-write "):
        return make_local_command("check_write_file", trimmed[13:].strip() or None)
    if trimmed == "/write" or trimmed.startswith("/write "):
        return make_local_command("write_file", trimmed[7:].strip() or None)
    if trimmed == "/check-write-files" or trimmed.startswith("/check-write-files "):
        return make_local_command("check_write_files", trimmed[19:].strip() or None)
    if trimmed == "/write-files" or trimmed.startswith("/write-files "):
        return make_local_command("write_files", trimmed[13:].strip() or None)
    if trimmed == "/check-edit" or trimmed.startswith("/check-edit "):
        return make_local_command("check_edit_file", trimmed[12:].strip() or None)
    if trimmed == "/edit" or trimmed.startswith("/edit "):
        return make_local_command("edit_file", trimmed[6:].strip() or None)
    if trimmed == "/check-multi-edit" or trimmed.startswith("/check-multi-edit "):
        return make_local_command("check_multi_edit_file", trimmed[18:].strip() or None)
    if trimmed == "/multi-edit" or trimmed.startswith("/multi-edit "):
        return make_local_command("multi_edit_file", trimmed[12:].strip() or None)
    if trimmed == "/check-delete" or trimmed.startswith("/check-delete "):
        return make_local_command("check_delete_file", trimmed[14:].strip() or None)
    if trimmed == "/delete" or trimmed.startswith("/delete "):
        return make_local_command("delete_file", trimmed[8:].strip() or None)
    if trimmed == "/check-delete-files" or trimmed.startswith("/check-delete-files "):
        return make_local_command("check_delete_files", trimmed[20:].strip() or None)
    if trimmed == "/delete-files" or trimmed.startswith("/delete-files "):
        return make_local_command("delete_files", trimmed[14:].strip() or None)
    if trimmed == "/check-move" or trimmed.startswith("/check-move "):
        return make_local_command("check_move_file", trimmed[12:].strip() or None)
    if trimmed == "/move" or trimmed.startswith("/move "):
        return make_local_command("move_file", trimmed[6:].strip() or None)
    if trimmed == "/check-move-files" or trimmed.startswith("/check-move-files "):
        return make_local_command("check_move_files", trimmed[18:].strip() or None)
    if trimmed == "/move-files" or trimmed.startswith("/move-files "):
        return make_local_command("move_files", trimmed[12:].strip() or None)
    if trimmed == "/check-copy" or trimmed.startswith("/check-copy "):
        return make_local_command("check_copy_file", trimmed[12:].strip() or None)
    if trimmed == "/copy" or trimmed.startswith("/copy "):
        return make_local_command("copy_file", trimmed[6:].strip() or None)
    if trimmed == "/check-copy-files" or trimmed.startswith("/check-copy-files "):
        return make_local_command("check_copy_files", trimmed[18:].strip() or None)
    if trimmed == "/copy-files" or trimmed.startswith("/copy-files "):
        return make_local_command("copy_files", trimmed[12:].strip() or None)
    if trimmed == "/check-move-dir" or trimmed.startswith("/check-move-dir "):
        return make_local_command("check_move_dir", trimmed[16:].strip() or None)
    if trimmed == "/move-dir" or trimmed.startswith("/move-dir "):
        return make_local_command("move_dir", trimmed[10:].strip() or None)
    if trimmed == "/check-move-dirs" or trimmed.startswith("/check-move-dirs "):
        return make_local_command("check_move_dirs", trimmed[17:].strip() or None)
    if trimmed == "/move-dirs" or trimmed.startswith("/move-dirs "):
        return make_local_command("move_dirs", trimmed[11:].strip() or None)
    if trimmed == "/check-copy-dir" or trimmed.startswith("/check-copy-dir "):
        return make_local_command("check_copy_dir", trimmed[16:].strip() or None)
    if trimmed == "/copy-dir" or trimmed.startswith("/copy-dir "):
        return make_local_command("copy_dir", trimmed[10:].strip() or None)
    if trimmed == "/check-copy-dirs" or trimmed.startswith("/check-copy-dirs "):
        return make_local_command("check_copy_dirs", trimmed[17:].strip() or None)
    if trimmed == "/copy-dirs" or trimmed.startswith("/copy-dirs "):
        return make_local_command("copy_dirs", trimmed[11:].strip() or None)
    if trimmed == "/check-mkdir" or trimmed.startswith("/check-mkdir "):
        return make_local_command("check_create_dir", trimmed[13:].strip() or None)
    if trimmed == "/mkdir" or trimmed.startswith("/mkdir "):
        return make_local_command("create_dir", trimmed[7:].strip() or None)
    if trimmed == "/check-mkdirs" or trimmed.startswith("/check-mkdirs "):
        return make_local_command("check_create_dirs", trimmed[14:].strip() or None)
    if trimmed == "/mkdirs" or trimmed.startswith("/mkdirs "):
        return make_local_command("create_dirs", trimmed[8:].strip() or None)
    if trimmed == "/check-rmdir" or trimmed.startswith("/check-rmdir "):
        return make_local_command("check_delete_empty_dir", trimmed[13:].strip() or None)
    if trimmed == "/rmdir" or trimmed.startswith("/rmdir "):
        return make_local_command("delete_empty_dir", trimmed[7:].strip() or None)
    if trimmed == "/check-rmdirs" or trimmed.startswith("/check-rmdirs "):
        return make_local_command("check_delete_empty_dirs", trimmed[14:].strip() or None)
    if trimmed == "/rmdirs" or trimmed.startswith("/rmdirs "):
        return make_local_command("delete_empty_dirs", trimmed[8:].strip() or None)
    if trimmed == "/check-executable" or trimmed.startswith("/check-executable "):
        return make_local_command("check_set_executable", trimmed[18:].strip() or None)
    if trimmed == "/set-executable" or trimmed.startswith("/set-executable "):
        return make_local_command("set_executable", trimmed[16:].strip() or None)
    if trimmed == "/check-patch" or trimmed.startswith("/check-patch "):
        return make_local_command("check_patch", trimmed[13:].strip() or None)
    if trimmed == "/patch" or trimmed.startswith("/patch "):
        return make_local_command("patch_file", trimmed[7:].strip() or None)
    if trimmed == "/check-patches" or trimmed.startswith("/check-patches "):
        return make_local_command("check_patches", trimmed[15:].strip() or None)
    if trimmed == "/patches" or trimmed.startswith("/patches "):
        return make_local_command("patch_files", trimmed[9:].strip() or None)
    if trimmed == "/check-regex-replace" or trimmed.startswith("/check-regex-replace "):
        return make_local_command("check_regex_replace", trimmed[21:].strip() or None)
    if trimmed == "/regex-replace" or trimmed.startswith("/regex-replace "):
        return make_local_command("regex_replace", trimmed[15:].strip() or None)
    return None
