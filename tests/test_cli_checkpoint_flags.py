import io
import json
import subprocess
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliCheckpointFlagTests(unittest.TestCase):
    def test_main_runs_checkpoint_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoint_text", return_value="Checkpoint:\n  created: yes") as get_checkpoint_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoint", "before tests"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoint:", stdout.getvalue())
        get_checkpoint_text.assert_called_once_with(Path(base).resolve(), "before tests")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoints_text", return_value="Checkpoints:\n  total: 1") as get_checkpoints_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoints"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoints:", stdout.getvalue())
        get_checkpoints_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoint_show_text", return_value="Checkpoint:\n  id: ckpt-1") as get_checkpoint_show_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoint-show", "ckpt-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoint:", stdout.getvalue())
        get_checkpoint_show_text.assert_called_once_with("ckpt-1", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoint_diff_text", return_value="Checkpoint diff:\n  id: ckpt-1") as get_checkpoint_diff_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoint-diff", "ckpt-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoint diff:", stdout.getvalue())
        get_checkpoint_diff_text.assert_called_once_with("ckpt-1", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoint_status_text", return_value="Checkpoint status:\n  matches: yes") as get_checkpoint_status_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoint-status", "ckpt-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoint status:", stdout.getvalue())
        get_checkpoint_status_text.assert_called_once_with("ckpt-1", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_checkpoint_restore_text", return_value="Check checkpoint restore:\n  ok: yes") as get_check_checkpoint_restore_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-checkpoint-restore", "ckpt-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check checkpoint restore:", stdout.getvalue())
        get_check_checkpoint_restore_text.assert_called_once_with("ckpt-1", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "canRestore": True,
                "restored": False,
                "matches": True,
                "id": "ckpt-1",
                "savedHead": "abc123",
                "currentHead": "abc123",
                "saved": {"untrackedFiles": 0, "stagedPatchChars": 0, "unstagedPatchChars": 0},
                "current": {"untrackedFiles": 0},
                "message": "Checkpoint can be restored.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_checkpoint_restore_report", return_value=report) as get_check_checkpoint_restore_report,
                patch("vibeagent.cli.format_check_checkpoint_restore_report_text", return_value="Check checkpoint restore:\n  ok: yes") as format_check_checkpoint_restore_report_text,
                patch("vibeagent.cli.get_check_checkpoint_restore_text") as get_check_checkpoint_restore_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--check-checkpoint-restore", "ckpt-1"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["checkCheckpointRestore"], report)
        self.assertEqual(payload["text"], "Check checkpoint restore:\n  ok: yes")
        get_check_checkpoint_restore_report.assert_called_once_with("ckpt-1", Path(base).resolve())
        format_check_checkpoint_restore_report_text.assert_called_once_with(report)
        get_check_checkpoint_restore_text.assert_not_called()
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoint_restore_text", return_value="Checkpoint restore:\n  restored: yes") as get_checkpoint_restore_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoint-restore", "ckpt-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoint restore:", stdout.getvalue())
        get_checkpoint_restore_text.assert_called_once_with("ckpt-1", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_checkpoint_delete_text", return_value="Check checkpoint delete:\n  canDelete: yes") as get_check_checkpoint_delete_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-checkpoint-delete", "ckpt-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check checkpoint delete:", stdout.getvalue())
        get_check_checkpoint_delete_text.assert_called_once_with("ckpt-1", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoint_delete_text", return_value="Checkpoint delete:\n  deleted: yes") as get_checkpoint_delete_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoint-delete", "ckpt-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoint delete:", stdout.getvalue())
        get_checkpoint_delete_text.assert_called_once_with("ckpt-1", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_checkpoint_prune_text", return_value="Check checkpoint prune:\n  deleteCount: 2") as get_check_checkpoint_prune_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-checkpoint-prune", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check checkpoint prune:", stdout.getvalue())
        get_check_checkpoint_prune_text.assert_called_once_with("2", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoint_prune_text", return_value="Checkpoint prune:\n  deleted: 2") as get_checkpoint_prune_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoint-prune", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoint prune:", stdout.getvalue())
        get_checkpoint_prune_text.assert_called_once_with("2", Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_checkpoint_local_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (
                ["--checkpoint", "before tests"],
                "vibeagent.cli.get_checkpoint_text",
                "Checkpoint:\n  created: no\n  message: git status failed",
                1,
            ),
            (
                ["--checkpoint-show", "missing"],
                "vibeagent.cli.get_checkpoint_show_text",
                "Checkpoint not found: missing",
                1,
            ),
            (
                ["--checkpoint-status", "ckpt-1"],
                "vibeagent.cli.get_checkpoint_status_text",
                "Checkpoint status:\n  matches: no\n  message: Current worktree differs from checkpoint.",
                1,
            ),
            (
                ["--checkpoint-restore", "ckpt-1"],
                "vibeagent.cli.get_checkpoint_restore_text",
                "Checkpoint restore:\n  restored: no\n  message: Current worktree differs from checkpoint.",
                1,
            ),
            (
                ["--check-checkpoint-delete", "missing"],
                "vibeagent.cli.get_check_checkpoint_delete_text",
                "Check checkpoint delete:\n  canDelete: no\n  message: Checkpoint not found: missing",
                1,
            ),
            (
                ["--check-checkpoint-prune", "-1"],
                "vibeagent.cli.get_check_checkpoint_prune_text",
                "Usage: /check-checkpoint-prune <keep-last>\nError: keep-last must be at least 0.",
                2,
            ),
        ]

        for argv_tail, patch_target, text, expected_exit_code in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text),
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, expected_exit_code)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            create_chat_client.assert_not_called()

    def test_main_checkpoint_delete_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--checkpoint-delete", "missing"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertIn("Checkpoint delete:", payload["text"])
        self.assertIn("Checkpoint not found: missing", payload["text"])
        self.assertFalse(payload["checkpointDelete"]["ok"])
        self.assertFalse(payload["checkpointDelete"]["deleted"])
        self.assertEqual(payload["checkpointDelete"]["id"], "missing")
        create_chat_client.assert_not_called()

    def test_main_checkpoint_json_outputs_structured_payload_without_duplicate_create(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("old\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("new\n", encoding="utf-8")

            create_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(create_stdout),
            ):
                create_exit = main(["--json", "--cwd", base, "--checkpoint", "before json"])

            list_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as list_create_chat_client,
                redirect_stdout(list_stdout),
            ):
                list_exit = main(["--json", "--cwd", base, "--checkpoints"])

        create_payload = json.loads(create_stdout.getvalue())
        list_payload = json.loads(list_stdout.getvalue())
        checkpoint = create_payload["checkpoint"]["checkpoint"]
        checkpoint_id = checkpoint["id"]

        self.assertEqual(create_exit, 0)
        self.assertEqual(create_payload["kind"], "local")
        self.assertTrue(create_payload["success"])
        self.assertTrue(create_payload["checkpoint"]["created"])
        self.assertEqual(checkpoint["label"], "before json")
        self.assertEqual(checkpoint["changedFiles"], 1)
        self.assertEqual(list_exit, 0)
        self.assertEqual(list_payload["checkpoints"]["total"], 1)
        self.assertEqual(list_payload["checkpoints"]["checkpoints"][0]["id"], checkpoint_id)
        create_chat_client.assert_not_called()
        list_create_chat_client.assert_not_called()

    def test_main_checkpoint_restore_and_delete_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("checkpoint\n", encoding="utf-8")

            create_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(create_stdout),
            ):
                create_exit = main(["--json", "--cwd", base, "--checkpoint", "restore json"])
            checkpoint_id = json.loads(create_stdout.getvalue())["checkpoint"]["checkpoint"]["id"]
            (root / "app.py").write_text("broken\n", encoding="utf-8")

            restore_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as restore_create_chat_client,
                redirect_stdout(restore_stdout),
            ):
                restore_exit = main(["--json", "--cwd", base, "--checkpoint-restore", checkpoint_id])

            delete_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as delete_create_chat_client,
                redirect_stdout(delete_stdout),
            ):
                delete_exit = main(["--json", "--cwd", base, "--checkpoint-delete", checkpoint_id])

            final_content = (root / "app.py").read_text(encoding="utf-8")

        restore_payload = json.loads(restore_stdout.getvalue())
        delete_payload = json.loads(delete_stdout.getvalue())

        self.assertEqual(create_exit, 0)
        self.assertEqual(restore_exit, 0)
        self.assertTrue(restore_payload["checkpointRestore"]["restored"])
        self.assertTrue(restore_payload["checkpointRestore"]["matches"])
        self.assertEqual(restore_payload["checkpointRestore"]["id"], checkpoint_id)
        self.assertEqual(final_content, "checkpoint\n")
        self.assertEqual(delete_exit, 0)
        self.assertTrue(delete_payload["checkpointDelete"]["deleted"])
        self.assertEqual(delete_payload["checkpointDelete"]["id"], checkpoint_id)
        create_chat_client.assert_not_called()
        restore_create_chat_client.assert_not_called()
        delete_create_chat_client.assert_not_called()

    def test_main_checkpoint_prune_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            created_ids = []
            for index in range(3):
                (root / "app.py").write_text(f"change {index}\n", encoding="utf-8")
                create_stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(create_stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, "--checkpoint", f"prune {index}"])
                self.assertEqual(exit_code, 0)
                created_ids.append(json.loads(create_stdout.getvalue())["checkpoint"]["checkpoint"]["id"])
                create_chat_client.assert_not_called()
                time.sleep(0.002)

            prune_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as prune_create_chat_client,
                redirect_stdout(prune_stdout),
            ):
                prune_exit = main(["--json", "--cwd", base, "--checkpoint-prune", "1"])

            list_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as list_create_chat_client,
                redirect_stdout(list_stdout),
            ):
                list_exit = main(["--json", "--cwd", base, "--checkpoints"])

        prune_payload = json.loads(prune_stdout.getvalue())
        list_payload = json.loads(list_stdout.getvalue())

        self.assertEqual(prune_exit, 0)
        self.assertEqual(prune_payload["checkpointPrune"]["total"], 3)
        self.assertEqual(prune_payload["checkpointPrune"]["deleted"], 2)
        self.assertEqual([item["id"] for item in prune_payload["checkpointPrune"]["checkpoints"]], [created_ids[1], created_ids[0]])
        self.assertEqual(list_exit, 0)
        self.assertEqual(list_payload["checkpoints"]["total"], 1)
        self.assertEqual(list_payload["checkpoints"]["checkpoints"][0]["id"], created_ids[2])
        prune_create_chat_client.assert_not_called()
        list_create_chat_client.assert_not_called()
