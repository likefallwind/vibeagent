from __future__ import annotations

from .command_types import LocalCommand, make_local_command


def parse_checkpoint_local_command(trimmed: str) -> LocalCommand | None:
    if trimmed == "/checkpoint" or trimmed.startswith("/checkpoint "):
        return make_local_command("checkpoint", trimmed[11:].strip() or None)
    if trimmed == "/checkpoints":
        return make_local_command("checkpoints", None)
    if trimmed == "/checkpoint-show" or trimmed.startswith("/checkpoint-show "):
        return make_local_command("checkpoint_show", trimmed[16:].strip() or None)
    if trimmed == "/checkpoint-diff" or trimmed.startswith("/checkpoint-diff "):
        return make_local_command("checkpoint_diff", trimmed[16:].strip() or None)
    if trimmed == "/checkpoint-status" or trimmed.startswith("/checkpoint-status "):
        return make_local_command("checkpoint_status", trimmed[18:].strip() or None)
    if trimmed == "/check-checkpoint-restore" or trimmed.startswith("/check-checkpoint-restore "):
        return make_local_command("check_checkpoint_restore", trimmed[26:].strip() or None)
    if trimmed == "/checkpoint-restore" or trimmed.startswith("/checkpoint-restore "):
        return make_local_command("checkpoint_restore", trimmed[20:].strip() or None)
    if trimmed == "/check-checkpoint-delete" or trimmed.startswith("/check-checkpoint-delete "):
        prefix = "/check-checkpoint-delete"
        return make_local_command("check_checkpoint_delete", trimmed[len(prefix) :].strip() or None)
    if trimmed == "/checkpoint-delete" or trimmed.startswith("/checkpoint-delete "):
        return make_local_command("checkpoint_delete", trimmed[19:].strip() or None)
    if trimmed == "/check-checkpoint-prune" or trimmed.startswith("/check-checkpoint-prune "):
        prefix = "/check-checkpoint-prune"
        return make_local_command("check_checkpoint_prune", trimmed[len(prefix) :].strip() or None)
    if trimmed == "/checkpoint-prune" or trimmed.startswith("/checkpoint-prune "):
        prefix = "/checkpoint-prune"
        return make_local_command("checkpoint_prune", trimmed[len(prefix) :].strip() or None)
    return None
