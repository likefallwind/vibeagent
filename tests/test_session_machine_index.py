from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from vibeagent.agent import run_agent
from vibeagent.cli import main
from vibeagent.cli_args import parse_args
from vibeagent.cli_machine_resume import prepare_machine_session_resume
from vibeagent.cli_ephemeral_session import ephemeral_session_scope
from vibeagent.session_machine_index import (
    backfill_project_session_index,
    is_machine_searchable_session_id,
    register_machine_session,
    resolve_machine_session_root,
)
from vibeagent.workspace_core import make_run_id
from vibeagent.types import AssistantResponse


class FinalClient:
    def complete(
        self,
        messages,
        tools=None,
        max_tokens=4096,
        temperature=0.2,
        timeout_ms=120_000,
    ):
        content = [{"type": "text", "text": "Index registration complete."}]
        return AssistantResponse(content=content, raw={"content": content})


class SessionMachineIndexTests(unittest.TestCase):
    def test_registers_private_exact_id_record_and_resolves_another_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-machine-index-") as base:
            root = Path(base)
            home = root / "home"
            source = root / "source"
            current = root / "current"
            source.mkdir()
            current.mkdir()
            run_id = make_run_id()
            self._write_session(source, run_id)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                record = register_machine_session(source, run_id)
                original_mtime = record.stat().st_mtime_ns
                register_machine_session(source, run_id)
                resolved = resolve_machine_session_root(current, run_id)

            self.assertEqual(resolved, source.resolve())
            self.assertEqual(record.stat().st_mode & 0o777, 0o600)
            self.assertEqual(record.stat().st_mtime_ns, original_mtime)
            self.assertEqual(record.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(record.parent.parent.stat().st_mode & 0o777, 0o700)
            payload = json.loads(record.read_text(encoding="utf-8"))
            self.assertEqual(payload["runId"], run_id)
            self.assertEqual(payload["projectRoot"], str(source.resolve()))
            self.assertNotIn("task", payload)

    def test_backfills_existing_sessions_but_never_indexes_names(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-machine-index-") as base:
            root = Path(base)
            home = root / "home"
            source = root / "source"
            current = root / "current"
            source.mkdir()
            current.mkdir()
            generated = make_run_id()
            self._write_session(source, generated)
            self._write_session(source, "named-session")

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                registered, failed = backfill_project_session_index(source)
                generated_root = resolve_machine_session_root(current, generated)
                named_root = resolve_machine_session_root(current, "named-session")

            self.assertEqual((registered, failed), (1, 1))
            self.assertEqual(generated_root, source.resolve())
            self.assertIsNone(named_root)

    def test_agent_task_event_registers_new_session_for_later_machine_resume(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-machine-index-") as base:
            root = Path(base)
            home = root / "home"
            source = root / "source"
            current = root / "current"
            source.mkdir()
            current.mkdir()

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                result = run_agent("Inspect the project", FinalClient(), base_dir=source)
                resolved = resolve_machine_session_root(current, result.run_id)

            self.assertTrue(result.success)
            self.assertEqual(resolved, source.resolve())

    def test_ephemeral_agent_session_is_not_registered(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-machine-index-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            project.mkdir()

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                with ephemeral_session_scope(project) as ephemeral:
                    result = run_agent(
                        "Inspect without persistence",
                        FinalClient(),
                        workspace=ephemeral.workspace,
                    )
                records = list((home / ".vibeagent" / "session-index").glob("*.json"))

            self.assertTrue(result.success)
            self.assertEqual(records, [])

    def test_duplicate_exact_id_is_ambiguous_and_tampered_records_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-machine-index-") as base:
            root = Path(base)
            home = root / "home"
            first = root / "first"
            second = root / "second"
            current = root / "current"
            for project in (first, second, current):
                project.mkdir()
            run_id = str(uuid4())
            self._write_session(first, run_id)
            self._write_session(second, run_id)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                first_record = register_machine_session(first, run_id)
                register_machine_session(second, run_id)
                with self.assertRaisesRegex(ValueError, "ambiguous"):
                    resolve_machine_session_root(current, run_id)
                first_record.write_text(
                    json.dumps(
                        {
                            "version": 1,
                            "runId": run_id,
                            "projectRoot": str(current.resolve()),
                            "updatedAt": 1,
                        }
                    ),
                    encoding="utf-8",
                )
                resolved = resolve_machine_session_root(current, run_id)

            self.assertEqual(resolved, second.resolve())

    @unittest.skipUnless(hasattr(os, "getuid"), "POSIX permissions are required")
    def test_group_readable_record_is_not_trusted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-machine-index-") as base:
            root = Path(base)
            home = root / "home"
            source = root / "source"
            current = root / "current"
            source.mkdir()
            current.mkdir()
            run_id = make_run_id()
            self._write_session(source, run_id)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                record = register_machine_session(source, run_id)
                record.chmod(0o644)
                resolved = resolve_machine_session_root(current, run_id)

            self.assertIsNone(resolved)

    def test_cli_preparation_switches_only_for_exact_machine_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-machine-index-") as base:
            root = Path(base)
            home = root / "home"
            source = root / "source"
            current = root / "current"
            source.mkdir()
            current.mkdir()
            run_id = make_run_id()
            self._write_session(source, run_id)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                register_machine_session(source, run_id)
                exact = parse_args(["--cwd", str(current), "--resume", run_id])
                prepare_machine_session_resume(exact)
                named = parse_args(["--cwd", str(current), "--resume", "session-name"])
                prepare_machine_session_resume(named)

            self.assertEqual(Path(exact.cwd), source.resolve())
            self.assertEqual(Path(named.cwd), current)

    def test_main_routes_cross_project_resume_before_one_shot_setup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-machine-index-") as base:
            root = Path(base)
            home = root / "home"
            source = root / "source"
            current = root / "current"
            source.mkdir()
            current.mkdir()
            run_id = make_run_id()
            self._write_session(source, run_id)

            with (
                patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}),
                patch("vibeagent.cli.run_one_shot", return_value=0) as run_one_shot,
            ):
                register_machine_session(source, run_id)
                exit_code = main(["--cwd", str(current), "--resume", run_id, "continue"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(Path(run_one_shot.call_args.kwargs["base_dir"]), source.resolve())
            self.assertEqual(run_one_shot.call_args.kwargs["resume_arg"], run_id)

    def test_machine_searchable_ids_are_strict(self) -> None:
        self.assertTrue(is_machine_searchable_session_id(make_run_id()))
        session_uuid = str(uuid4())
        self.assertTrue(is_machine_searchable_session_id(session_uuid))
        self.assertFalse(is_machine_searchable_session_id(session_uuid.upper()))
        self.assertFalse(is_machine_searchable_session_id("run-1"))
        self.assertFalse(is_machine_searchable_session_id("session-name"))
        self.assertFalse(is_machine_searchable_session_id("../escape"))

    @staticmethod
    def _write_session(root: Path, run_id: str) -> None:
        directory = root / ".vibeagent" / "sessions" / run_id
        directory.mkdir(parents=True)
        (directory / "events.jsonl").write_text(
            json.dumps({"type": "task", "task": "inspect"}) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
