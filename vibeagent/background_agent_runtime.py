from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
import uuid

from .background_agent_config import (
    background_agent_config_path,
    create_background_agent_config,
    read_background_agent_config,
)
from .background_agent_attachment import background_agent_attachment_path
from .background_agent_approval import remove_background_approval
from .background_agent_input import remove_background_user_input
from .background_agent_inbox import (
    enqueue_background_agent_message,
    pending_background_agent_message_count,
    remove_background_agent_inbox,
)
from .background_agent_lock import background_agent_transition_lock
from .background_agent_process import (
    spawn_background_agent_worker,
    start_background_process_reaper,
)
from .background_agent_store import (
    as_process_record,
    background_agent_record_path,
    background_agent_runtime_root,
    background_agent_view,
    background_agent_view_payload as _background_agent_view_payload,
    ensure_background_agent_runtime_root,
    ensure_private_directory,
    get_background_agent,
    list_background_agents,
    write_background_agent_record,
    write_private_text,
    write_private_text_atomic,
)
from .background_agent_types import (
    DEFAULT_BACKGROUND_AGENT_LOG_CHARS,
    MAX_BACKGROUND_AGENT_LOG_CHARS,
    BackgroundAgentBatchRespawn,
    BackgroundAgentRecord,
    BackgroundAgentView,
)
from .process_registry import read_process_start_ticks, terminate_persistent_process
from .redaction import redact_sensitive_text


def launch_background_agent(
    project_root: Path,
    invocation_root: Path,
    argv: list[str],
    *,
    task_summary: str,
    session_name: str | None,
    resume_reference: str | None = None,
) -> BackgroundAgentView:
    root = project_root.resolve()
    invocation = invocation_root.resolve()
    agent_id = uuid.uuid4().hex[:12]
    runtime_root = ensure_background_agent_runtime_root(root)
    logs_root = ensure_private_directory(runtime_root / "logs")
    stdout_path = logs_root / f"{agent_id}.stdout.log"
    stderr_path = logs_root / f"{agent_id}.stderr.log"
    exit_code_path = logs_root / f"{agent_id}.exitcode"
    stopped_path = logs_root / f"{agent_id}.stopped"

    child_argv = _without_background_flag(argv)
    if not _contains_option(child_argv, {"-p", "--print"}):
        child_argv.insert(0, "--print")
    effective_session_name = session_name
    if effective_session_name is None and resume_reference is None:
        effective_session_name = f"background-{agent_id}"
        child_argv[0:0] = ["--name", effective_session_name]
    effective_resume_reference = (
        (resume_reference.strip() if isinstance(resume_reference, str) else "")
        or effective_session_name
    )
    if not effective_resume_reference:
        raise ValueError("Background resume could not resolve its source session.")
    try:
        config = create_background_agent_config(
            root,
            agent_id,
            session_root=root,
            resume_reference=effective_resume_reference,
            base_argv=child_argv,
        )
        write_private_text(exit_code_path, "", exclusive=True)
        process = spawn_background_agent_worker(
            config,
            invocation_root=invocation,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            exit_code_path=exit_code_path,
            initial_argv=child_argv,
            append_logs=False,
        )
    except Exception:
        _remove_background_agent_metadata(root, agent_id)
        _remove_paths(stdout_path, stderr_path, exit_code_path)
        raise

    record = BackgroundAgentRecord(
        id=agent_id,
        project_root=root,
        invocation_root=invocation,
        pid=process.pid,
        start_ticks=read_process_start_ticks(process.pid),
        started_at=datetime.now(UTC).isoformat(timespec="seconds"),
        task_summary=_task_summary(task_summary),
        session_name=effective_session_name or effective_resume_reference,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        exit_code_path=exit_code_path,
        stopped_path=stopped_path,
    )
    try:
        write_background_agent_record(record)
    except Exception:
        terminate_persistent_process(as_process_record(record))
        start_background_process_reaper(process)
        _remove_background_agent_metadata(root, agent_id)
        _remove_paths(stdout_path, stderr_path, exit_code_path)
        raise
    start_background_process_reaper(process)
    return background_agent_view(record)


def send_background_agent_message(
    project_root: Path,
    agent_id: str,
    message: str,
) -> tuple[BackgroundAgentView | None, str]:
    root = project_root.resolve()
    with background_agent_transition_lock(root, agent_id):
        view = get_background_agent(root, agent_id)
        if view is None:
            return None, "not-found"
        _reject_attached_background_agent(view)
        config = read_background_agent_config(root, agent_id)
        enqueue_background_agent_message(config, message)
        if view.status in {"running", "needs-input"}:
            return background_agent_view(view.record), "queued"
        return _respawn_background_agent_locked(view, config, task_summary=message), "respawned"


def respawn_background_agent(
    project_root: Path,
    agent_id: str,
) -> tuple[BackgroundAgentView | None, str]:
    root = project_root.resolve()
    with background_agent_transition_lock(root, agent_id):
        view = get_background_agent(root, agent_id)
        if view is None:
            return None, "not-found"
        return _respawn_existing_background_agent_locked(root, view), "respawned"


def respawn_inactive_background_agents(
    project_root: Path,
) -> BackgroundAgentBatchRespawn:
    root = project_root.resolve()
    candidate_ids = tuple(
        view.record.id
        for view in list_background_agents(root)
        if view.status in {"stopped", "completed", "failed", "lost"}
    )
    respawned: list[BackgroundAgentView] = []
    failures: list[tuple[str, str]] = []
    for agent_id in candidate_ids:
        try:
            with background_agent_transition_lock(root, agent_id):
                view = get_background_agent(root, agent_id)
                if view is None:
                    failures.append((agent_id, "Background agent no longer exists."))
                    continue
                if view.status not in {"stopped", "completed", "failed", "lost"}:
                    failures.append(
                        (agent_id, f"Background agent is now {view.status}; it was not restarted.")
                    )
                    continue
                respawned.append(_respawn_existing_background_agent_locked(root, view))
        except (OSError, RuntimeError, ValueError) as error:
            failures.append((agent_id, str(error)))
    return BackgroundAgentBatchRespawn(
        eligible_count=len(candidate_ids),
        respawned=tuple(respawned),
        failures=tuple(failures),
    )


def _respawn_existing_background_agent_locked(
    root: Path,
    view: BackgroundAgentView,
) -> BackgroundAgentView:
    agent_id = view.record.id
    _reject_attached_background_agent(view)
    if view.status in {"running", "needs-input", "approval-error", "input-error"}:
        terminate_persistent_process(as_process_record(view.record))
        remove_background_approval(root, agent_id)
        remove_background_user_input(root, agent_id)
    config = read_background_agent_config(root, agent_id)
    if pending_background_agent_message_count(root, agent_id) == 0:
        message = "Continue the interrupted background task from the recorded session context."
        enqueue_background_agent_message(config, message)
    else:
        message = "Continue with the queued background messages from the recorded session context."
    return _respawn_background_agent_locked(view, config, task_summary=message)


def stop_background_agent(project_root: Path, agent_id: str) -> BackgroundAgentView | None:
    root = project_root.resolve()
    with background_agent_transition_lock(root, agent_id):
        view = get_background_agent(root, agent_id)
        if view is None:
            return None
        _reject_attached_background_agent(view)
        if view.status in {"running", "needs-input", "approval-error", "input-error"}:
            terminate_persistent_process(as_process_record(view.record))
            remove_background_approval(root, agent_id)
            remove_background_user_input(root, agent_id)
            write_private_text(view.record.stopped_path, "stopped\n", exclusive=False)
        return background_agent_view(view.record)


def remove_background_agent(project_root: Path, agent_id: str) -> tuple[bool, str]:
    root = project_root.resolve()
    with background_agent_transition_lock(root, agent_id):
        view = get_background_agent(root, agent_id)
        if view is None:
            return False, f"Background agent not found: {agent_id}"
        _reject_attached_background_agent(view)
        if view.status in {"running", "needs-input", "approval-error", "input-error"}:
            return False, f"Background agent is still running: {agent_id}"
        record_path = background_agent_record_path(root, agent_id)
        _remove_background_agent_metadata(root, agent_id)
        _remove_paths(
            view.record.stdout_path,
            view.record.stderr_path,
            view.record.exit_code_path,
            view.record.stopped_path,
            record_path,
        )
    return True, f"Removed background agent {agent_id}. Session transcript was preserved."


def read_background_agent_logs(
    project_root: Path,
    agent_id: str,
    *,
    max_chars: int = DEFAULT_BACKGROUND_AGENT_LOG_CHARS,
) -> tuple[BackgroundAgentView | None, str, str]:
    view = get_background_agent(project_root, agent_id)
    if view is None:
        return None, "", ""
    bounded = max(1_000, min(max_chars, MAX_BACKGROUND_AGENT_LOG_CHARS))
    return (
        view,
        _read_text_tail(view.record.stdout_path, bounded),
        _read_text_tail(view.record.stderr_path, bounded),
    )


def background_agent_view_payload(view: BackgroundAgentView) -> dict[str, object]:
    payload = _background_agent_view_payload(view)
    payload["pendingMessages"] = pending_background_agent_message_count(
        view.record.project_root,
        view.record.id,
    )
    return payload


def _task_summary(task: str) -> str:
    return " ".join(redact_sensitive_text(task).split())[:500]


def _without_background_flag(argv: list[str]) -> list[str]:
    result: list[str] = []
    options = True
    for item in argv:
        if options and item == "--":
            options = False
            result.append(item)
        elif options and item in {"--background", "--bg"}:
            continue
        else:
            result.append(item)
    return result


def _contains_option(argv: list[str], names: set[str]) -> bool:
    for item in argv:
        if item == "--":
            return False
        if item in names or any(
            item.startswith(f"{name}=") for name in names if name.startswith("--")
        ):
            return True
    return False


def _read_text_tail(path: Path, max_chars: int) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(text) <= max_chars:
        return text
    return f"[truncated to last {max_chars} chars]\n{text[-max_chars:]}"


def _remove_paths(*paths: Path | None) -> None:
    for path in paths:
        if path is not None:
            path.unlink(missing_ok=True)


def _respawn_background_agent_locked(
    view: BackgroundAgentView,
    config,
    *,
    task_summary: str,
) -> BackgroundAgentView:
    record = view.record
    was_stopped = record.stopped_path.is_file()
    try:
        remove_background_approval(record.project_root, record.id)
        remove_background_user_input(record.project_root, record.id)
        write_private_text_atomic(record.exit_code_path, "")
        record.stopped_path.unlink(missing_ok=True)
        process = spawn_background_agent_worker(
            config,
            invocation_root=record.invocation_root,
            stdout_path=record.stdout_path,
            stderr_path=record.stderr_path,
            exit_code_path=record.exit_code_path,
            initial_argv=None,
            append_logs=True,
        )
    except Exception:
        _restore_background_agent_terminal_state(view, was_stopped=was_stopped)
        raise
    updated = replace(
        record,
        pid=process.pid,
        start_ticks=read_process_start_ticks(process.pid),
        started_at=datetime.now(UTC).isoformat(timespec="seconds"),
        task_summary=_task_summary(task_summary),
    )
    try:
        write_background_agent_record(updated, exclusive=False)
    except Exception:
        terminate_persistent_process(as_process_record(updated))
        start_background_process_reaper(process)
        _restore_background_agent_terminal_state(view, was_stopped=was_stopped)
        raise
    start_background_process_reaper(process)
    return background_agent_view(updated)


def _remove_background_agent_metadata(project_root: Path, agent_id: str) -> None:
    background_agent_attachment_path(project_root, agent_id).unlink(missing_ok=True)
    background_agent_config_path(project_root, agent_id).unlink(missing_ok=True)
    remove_background_agent_inbox(project_root, agent_id)
    remove_background_approval(project_root, agent_id)
    remove_background_user_input(project_root, agent_id)
    launch_root = background_agent_runtime_root(project_root) / "launch"
    if launch_root.is_dir() and not launch_root.is_symlink():
        for path in launch_root.glob(f"{agent_id}-*.json"):
            if path.parent == launch_root and not path.is_symlink():
                path.unlink(missing_ok=True)
        legacy = launch_root / f"{agent_id}.json"
        if not legacy.is_symlink():
            legacy.unlink(missing_ok=True)


def _restore_background_agent_terminal_state(
    view: BackgroundAgentView,
    *,
    was_stopped: bool,
) -> None:
    text = f"{view.exit_code}\n" if view.exit_code is not None else ""
    write_private_text_atomic(view.record.exit_code_path, text)
    if was_stopped:
        write_private_text(view.record.stopped_path, "stopped\n", exclusive=False)


def _reject_attached_background_agent(view: BackgroundAgentView) -> None:
    if view.status == "attachment-error":
        raise ValueError(
            f"Background agent has an invalid attachment state: {view.record.id}"
        )
    if view.status in {"attaching", "attached"}:
        raise ValueError(
            f"Background agent is {view.status} in another terminal: {view.record.id}"
        )


__all__ = [
    "BackgroundAgentRecord",
    "BackgroundAgentView",
    "background_agent_record_path",
    "background_agent_runtime_root",
    "background_agent_view_payload",
    "get_background_agent",
    "launch_background_agent",
    "list_background_agents",
    "read_background_agent_logs",
    "remove_background_agent",
    "respawn_background_agent",
    "respawn_inactive_background_agents",
    "send_background_agent_message",
    "stop_background_agent",
]
