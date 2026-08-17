from __future__ import annotations

from contextlib import nullcontext, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent import background_agent_runtime as runtime
from vibeagent.background_agent_types import (
    BackgroundAgentBatchRespawn,
    BackgroundAgentRecord,
    BackgroundAgentView,
)
from vibeagent.cli import main
from vibeagent.cli_args import has_local_flag, parse_args
from vibeagent.cli_exit_codes import local_result_exit_code


AGENT_ID = "0123456789ab"


class CliBackgroundAgentCommandTests(unittest.TestCase):
    def test_parser_maps_lifecycle_commands_and_global_options(self) -> None:
        logs = parse_args(
            ["logs", AGENT_ID, "--max-chars", "5000", "--cwd", "/tmp", "--json"]
        )
        stop = parse_args(["--cwd", "/tmp", "kill", AGENT_ID])
        respawn_all = parse_args(["--json", "respawn", "--all", "--cwd", "/tmp"])
        remove = parse_args(["rm", AGENT_ID, "--output-format", "json"])
        ordinary = parse_args(["fix", "stop", "integration"])

        self.assertEqual(logs.background_agent_log, AGENT_ID)
        self.assertEqual(logs.background_agent_log_max_chars, 5000)
        self.assertEqual(logs.cwd, "/tmp")
        self.assertTrue(logs.json)
        self.assertEqual(stop.stop_background_agent, AGENT_ID)
        self.assertTrue(respawn_all.respawn_all_background_agents)
        self.assertEqual(remove.remove_background_agent, AGENT_ID)
        self.assertTrue(remove.json)
        self.assertTrue(has_local_flag(respawn_all))
        self.assertEqual(ordinary.task, ["fix", "stop", "integration"])
        self.assertIsNone(ordinary.stop_background_agent)

    def test_top_level_commands_are_provider_free(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-commands-") as base:
            root = Path(base)
            for command in ("logs", "stop", "kill", "respawn", "rm"):
                with self.subTest(command=command):
                    stdout = io.StringIO()
                    with (
                        patch("vibeagent.cli.create_chat_client") as create_chat_client,
                        redirect_stdout(stdout),
                    ):
                        exit_code = main([command, AGENT_ID, "--cwd", str(root)])

                    self.assertEqual(exit_code, 1)
                    self.assertIn("Background agent not found", stdout.getvalue())
                    create_chat_client.assert_not_called()

    def test_respawn_all_reports_machine_readable_success_without_provider(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-respawn-all-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    ["--cwd", base, "respawn", "--all", "--json"]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["backgroundAgentRespawnAll"]["eligible"], 0)
        self.assertEqual(payload["backgroundAgentRespawnAll"]["respawned"], [])
        create_chat_client.assert_not_called()

    def test_respawn_all_failure_count_sets_failed_exit_code(self) -> None:
        args = parse_args(["respawn", "--all"])

        exit_code = local_result_exit_code(
            args,
            "Background agent batch respawn:\n  eligible: 2\n  respawned: 1\n  failed: 1",
        )

        self.assertEqual(exit_code, 1)

    def test_batch_respawn_rechecks_each_candidate_under_transition_lock(self) -> None:
        root = Path("/tmp/project")
        stopped = _view(root, "0123456789ab", "stopped")
        changed = _view(root, "abcdef012345", "failed")
        now_running = _view(root, changed.record.id, "running")
        respawned = _view(root, stopped.record.id, "running")
        current = {
            stopped.record.id: stopped,
            changed.record.id: now_running,
        }

        with (
            patch.object(runtime, "list_background_agents", return_value=(stopped, changed)),
            patch.object(
                runtime,
                "background_agent_transition_lock",
                side_effect=lambda *_args: nullcontext(),
            ),
            patch.object(
                runtime,
                "get_background_agent",
                side_effect=lambda _root, agent_id: current[agent_id],
            ),
            patch.object(
                runtime,
                "_respawn_existing_background_agent_locked",
                return_value=respawned,
            ) as restart,
        ):
            result = runtime.respawn_inactive_background_agents(root)

        self.assertEqual(result.eligible_count, 2)
        self.assertEqual(result.respawned, (respawned,))
        self.assertEqual(result.failures[0][0], changed.record.id)
        self.assertIn("now running", result.failures[0][1])
        restart.assert_called_once_with(root, stopped)

    def test_local_batch_payload_preserves_partial_failures(self) -> None:
        root = Path("/tmp/project")
        respawned = _view(root, AGENT_ID, "running")
        result = BackgroundAgentBatchRespawn(
            eligible_count=2,
            respawned=(respawned,),
            failures=(("abcdef012345", "state changed"),),
        )
        args = parse_args(["respawn", "--all"])

        with patch(
            "vibeagent.cli_background_agent_local_flags.respawn_inactive_background_agents",
            return_value=result,
        ):
            from vibeagent.cli_background_agent_local_flags import (
                run_background_agent_local_flag,
            )

            text, payload = run_background_agent_local_flag(args, root, {})  # type: ignore[misc]

        self.assertIn("respawned: 1", text)
        self.assertIn("failed: 1", text)
        report = payload["backgroundAgentRespawnAll"]
        self.assertEqual(len(report["respawned"]), 1)  # type: ignore[index]
        self.assertEqual(report["failures"][0]["id"], "abcdef012345")  # type: ignore[index]


def _view(root: Path, agent_id: str, status: str) -> BackgroundAgentView:
    logs = root / ".vibeagent/background-agents/logs"
    record = BackgroundAgentRecord(
        id=agent_id,
        project_root=root,
        invocation_root=root,
        pid=123,
        start_ticks=1,
        started_at="2026-01-01T00:00:00+00:00",
        task_summary="task",
        session_name="session",
        stdout_path=logs / f"{agent_id}.stdout.log",
        stderr_path=logs / f"{agent_id}.stderr.log",
        exit_code_path=logs / f"{agent_id}.exitcode",
        stopped_path=logs / f"{agent_id}.stopped",
    )
    return BackgroundAgentView(record=record, status=status, exit_code=None)


if __name__ == "__main__":
    unittest.main()
