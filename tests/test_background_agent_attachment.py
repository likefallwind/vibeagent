from __future__ import annotations

from contextlib import contextmanager
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent import background_agent_process as process_runtime
from vibeagent import background_agent_runtime as runtime
from vibeagent import background_agent_store as store
from vibeagent.background_agent_attach import (
    BackgroundAgentAttachContext,
    attach_background_agent,
)
from vibeagent.background_agent_attachment import (
    claim_background_agent_attachment,
    read_background_agent_attachment,
    release_background_agent_attachment,
)
from vibeagent.background_agent_config import (
    BackgroundAgentConfig,
    background_agent_config_path,
    create_background_agent_config,
)
from vibeagent.background_agent_inbox import (
    enqueue_background_agent_message,
    pending_background_agent_message_count,
)
from vibeagent.background_agent_worker import run_worker
from vibeagent.cli import main
from vibeagent.cli_args import parse_args
from vibeagent.cli_background_agent_attach import attach_background_agent_from_cli


class BackgroundAgentAttachmentTests(unittest.TestCase):
    def test_private_attachment_claim_is_exclusive_and_released_by_owner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-attach-") as base:
            root = Path(base).resolve()
            agent_id = "0123456789ab"
            attachment = claim_background_agent_attachment(
                root,
                agent_id,
                waiting_for_worker=False,
            )
            path = root / ".vibeagent" / "background-agents" / "attachments" / f"{agent_id}.json"

            self.assertEqual(attachment.state, "attached")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(read_background_agent_attachment(root, agent_id), attachment)
            with self.assertRaisesRegex(ValueError, "already attached"):
                claim_background_agent_attachment(
                    root,
                    agent_id,
                    waiting_for_worker=False,
                )

            release_background_agent_attachment(root, agent_id)
            self.assertIsNone(read_background_agent_attachment(root, agent_id))

    def test_stale_attachment_is_removed_before_new_claim(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-attach-") as base:
            root = Path(base).resolve()
            agent_id = "0123456789ab"
            claim_background_agent_attachment(root, agent_id, waiting_for_worker=True)

            with patch(
                "vibeagent.background_agent_attachment._attachment_process_running",
                return_value=False,
            ):
                self.assertIsNone(read_background_agent_attachment(root, agent_id))

            replacement = claim_background_agent_attachment(
                root,
                agent_id,
                waiting_for_worker=False,
            )
            self.assertEqual(replacement.state, "attached")
            release_background_agent_attachment(root, agent_id)

    def test_worker_yields_after_active_turn_without_consuming_queued_message(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-attach-") as base:
            root = Path(base).resolve()
            agent_id = "0123456789ab"
            config = create_background_agent_config(
                root,
                agent_id,
                session_root=root,
                resume_reference="background-0123456789ab",
                base_argv=["--print", "initial"],
            )
            exit_path = root / ".vibeagent" / "background-agents" / "logs" / f"{agent_id}.exitcode"
            exit_path.parent.mkdir(parents=True)
            exit_path.write_text("", encoding="utf-8")
            payload_path = root / "payload.json"
            payload_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 2,
                        "agentId": agent_id,
                        "projectRoot": root.as_posix(),
                        "configPath": background_agent_config_path(root, agent_id).as_posix(),
                        "exitCodePath": exit_path.as_posix(),
                        "initialArgv": ["--print", "initial"],
                    }
                ),
                encoding="utf-8",
            )
            calls = 0

            def fake_main(_argv: list[str]) -> int:
                nonlocal calls
                calls += 1
                enqueue_background_agent_message(config, "queued while attaching")
                claim_background_agent_attachment(root, agent_id, waiting_for_worker=True)
                return 0

            try:
                self.assertEqual(run_worker(payload_path, cli_main_func=fake_main), 0)
                self.assertEqual(calls, 1)
                self.assertEqual(pending_background_agent_message_count(root, agent_id), 1)
                self.assertEqual(exit_path.read_text(encoding="utf-8"), "0\n")
            finally:
                release_background_agent_attachment(root, agent_id)

    def test_attach_waits_for_worker_then_exposes_attached_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-attach-") as base:
            root = Path(base).resolve()
            process = Mock(pid=12345)
            with (
                patch.object(process_runtime.subprocess, "Popen", return_value=process),
                patch.object(runtime, "read_process_start_ticks", return_value=77),
                patch.object(store, "persistent_process_running", return_value=True),
            ):
                view = runtime.launch_background_agent(
                    root,
                    root,
                    ["--background", "inspect"],
                    task_summary="inspect",
                    session_name=None,
                )

            waited = Mock()
            with patch(
                "vibeagent.background_agent_attach.persistent_process_running",
                side_effect=[True, False],
            ):
                with attach_background_agent(root, view.record.id, on_wait=waited) as attachment:
                    attached = runtime.get_background_agent(root, view.record.id)
                    self.assertEqual(attachment.config.agent_id, view.record.id)
                    self.assertEqual(attached.status, "attached")  # type: ignore[union-attr]
                    with self.assertRaisesRegex(ValueError, "attached"):
                        runtime.respawn_background_agent(root, view.record.id)

            waited.assert_called_once_with()
            self.assertIsNone(read_background_agent_attachment(root, view.record.id))

    def test_malformed_attachment_remains_visible_but_blocks_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-attach-") as base:
            root = Path(base).resolve()
            process = Mock(pid=12345)
            with (
                patch.object(process_runtime.subprocess, "Popen", return_value=process),
                patch.object(runtime, "read_process_start_ticks", return_value=77),
                patch.object(store, "persistent_process_running", return_value=True),
            ):
                view = runtime.launch_background_agent(
                    root,
                    root,
                    ["--background", "inspect"],
                    task_summary="inspect",
                    session_name=None,
                )
            attachment_path = (
                root
                / ".vibeagent"
                / "background-agents"
                / "attachments"
                / f"{view.record.id}.json"
            )
            attachment_path.parent.mkdir()
            attachment_path.write_text("not-json\n", encoding="utf-8")

            damaged = runtime.get_background_agent(root, view.record.id)
            self.assertEqual(damaged.status, "attachment-error")  # type: ignore[union-attr]
            with self.assertRaisesRegex(ValueError, "invalid attachment state"):
                runtime.send_background_agent_message(root, view.record.id, "continue")

    def test_cli_attach_routes_to_interactive_resume_in_recorded_worktree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-attach-") as base:
            root = Path(base).resolve()
            worktree = root / "worktree"
            invocation = root / "invocation"
            worktree.mkdir()
            invocation.mkdir()
            config = BackgroundAgentConfig(
                agent_id="0123456789ab",
                project_root=root,
                session_root=worktree,
                resume_reference="run-123",
                base_argv=("--print", "--model", "session-model", "initial"),
                worker_token="0" * 32,
            )
            observed_cwds: list[Path] = []
            captured = Mock(
                side_effect=lambda _args: observed_cwds.append(Path.cwd()) or 0
            )

            @contextmanager
            def fake_attach(*_args, **_kwargs):
                yield BackgroundAgentAttachContext(config, invocation)

            args = parse_args(
                ["--attach-background-agent", config.agent_id, "--cwd", root.as_posix()]
            )
            with (
                patch(
                    "vibeagent.cli_background_agent_attach.attach_background_agent",
                    side_effect=fake_attach,
                ),
                patch("sys.stdout", new=io.StringIO()),
            ):
                exit_code = attach_background_agent_from_cli(
                    args,
                    run_interactive_func=captured,
                )

            self.assertEqual(exit_code, 0)
            attached_args = captured.call_args.args[0]
            self.assertEqual(attached_args.cwd, worktree.as_posix())
            self.assertEqual(attached_args.resume, "run-123")
            self.assertEqual(attached_args.model, "session-model")
            self.assertEqual(attached_args.task, [])
            self.assertFalse(attached_args.print_mode)
            self.assertIsNone(attached_args.attach_background_agent)
            self.assertEqual(observed_cwds, [invocation])

    def test_main_routes_attach_before_normal_interactive_startup(self) -> None:
        with patch("vibeagent.cli.attach_background_agent_from_cli", return_value=0) as attach:
            flag_exit = main(["--attach-background-agent", "0123456789ab"])
            command_exit = main(["attach", "0123456789ab"])

        self.assertEqual(flag_exit, 0)
        self.assertEqual(command_exit, 0)
        self.assertEqual(attach.call_count, 2)

    def test_attach_rejects_task_and_explicit_resume(self) -> None:
        stdout = io.StringIO()
        with patch("sys.stdout", new=stdout):
            task_exit = main(["--attach-background-agent", "0123456789ab", "task"])
            resume_exit = main(
                ["--attach-background-agent", "0123456789ab", "--resume", "run-1"]
            )

        self.assertEqual(task_exit, 2)
        self.assertEqual(resume_exit, 2)
        self.assertIn("cannot be combined", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
