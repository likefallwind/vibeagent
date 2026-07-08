from __future__ import annotations

from .command_types import LocalCommand, make_local_command


def parse_git_local_command(trimmed: str) -> LocalCommand | None:
    if trimmed == "/git-status":
        return make_local_command("git_status", None)
    if trimmed == "/conflicts" or trimmed.startswith("/conflicts "):
        return make_local_command("git_conflicts", trimmed[10:].strip() or None)
    if trimmed == "/git-info":
        return make_local_command("git_info", None)
    if trimmed == "/branches":
        return make_local_command("branches", None)
    if trimmed == "/log" or trimmed.startswith("/log "):
        return make_local_command("log", trimmed[5:].strip() or None)
    if trimmed == "/show" or trimmed.startswith("/show "):
        return make_local_command("show", trimmed[6:].strip() or None)
    if trimmed == "/blame" or trimmed.startswith("/blame "):
        return make_local_command("blame", trimmed[7:].strip() or None)
    if trimmed == "/stashes" or trimmed.startswith("/stashes "):
        return make_local_command("stashes", trimmed[9:].strip() or None)
    if trimmed == "/check-fetch" or trimmed.startswith("/check-fetch "):
        return make_local_command("check_fetch", trimmed[13:].strip() or None)
    if trimmed == "/fetch" or trimmed.startswith("/fetch "):
        return make_local_command("fetch", trimmed[7:].strip() or None)
    if trimmed == "/check-pull":
        return make_local_command("check_pull", None)
    if trimmed == "/pull":
        return make_local_command("pull", None)
    if trimmed == "/check-push":
        return make_local_command("check_push", None)
    if trimmed == "/push":
        return make_local_command("push", None)
    if trimmed == "/check-stash" or trimmed.startswith("/check-stash "):
        return make_local_command("check_stash", trimmed[13:].strip() or None)
    if trimmed == "/stash" or trimmed.startswith("/stash "):
        return make_local_command("stash", trimmed[7:].strip() or None)
    if trimmed == "/check-stash-apply" or trimmed.startswith("/check-stash-apply "):
        return make_local_command("check_stash_apply", trimmed[19:].strip() or None)
    if trimmed == "/stash-apply" or trimmed.startswith("/stash-apply "):
        return make_local_command("stash_apply", trimmed[13:].strip() or None)
    if trimmed == "/check-stash-drop" or trimmed.startswith("/check-stash-drop "):
        return make_local_command("check_stash_drop", trimmed[18:].strip() or None)
    if trimmed == "/stash-drop" or trimmed.startswith("/stash-drop "):
        return make_local_command("stash_drop", trimmed[12:].strip() or None)
    if trimmed == "/check-stage" or trimmed.startswith("/check-stage "):
        return make_local_command("check_stage", trimmed[13:].strip() or None)
    if trimmed == "/stage" or trimmed.startswith("/stage "):
        return make_local_command("stage", trimmed[7:].strip() or None)
    if trimmed == "/check-unstage" or trimmed.startswith("/check-unstage "):
        return make_local_command("check_unstage", trimmed[15:].strip() or None)
    if trimmed == "/unstage" or trimmed.startswith("/unstage "):
        return make_local_command("unstage", trimmed[9:].strip() or None)
    if trimmed == "/check-commit" or trimmed.startswith("/check-commit "):
        return make_local_command("check_commit", trimmed[14:].strip() or None)
    if trimmed == "/commit" or trimmed.startswith("/commit "):
        return make_local_command("commit", trimmed[8:].strip() or None)
    if trimmed == "/check-restore" or trimmed.startswith("/check-restore "):
        return make_local_command("check_restore", trimmed[15:].strip() or None)
    if trimmed == "/restore" or trimmed.startswith("/restore "):
        return make_local_command("restore", trimmed[9:].strip() or None)
    if trimmed == "/check-switch" or trimmed.startswith("/check-switch "):
        return make_local_command("check_switch", trimmed[14:].strip() or None)
    if trimmed == "/switch" or trimmed.startswith("/switch "):
        return make_local_command("switch", trimmed[8:].strip() or None)
    return None
