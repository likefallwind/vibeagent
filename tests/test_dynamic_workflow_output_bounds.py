from __future__ import annotations

import os
from pathlib import Path
import tempfile
from threading import Event, Thread
import unittest
from unittest.mock import Mock, patch

from vibeagent.dynamic_workflow_node import _terminate_when_cancelled, run_node_workflow


class DynamicWorkflowOutputBoundsTests(unittest.TestCase):
    def test_cancel_watcher_exits_after_workflow_process_finishes(self) -> None:
        process = Mock()
        process.poll.side_effect = [None, 0]
        watcher = Thread(target=_terminate_when_cancelled, args=(Event(), process))

        watcher.start()
        watcher.join(timeout=1)

        self.assertFalse(watcher.is_alive())
        process.terminate.assert_not_called()

    def test_rejects_large_protocol_line_without_materializing_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workflow-output-") as base:
            root = Path(base)
            fake_node = self._write_fake_node(
                root,
                "import os, sys\n"
                "sys.stdin.readline()\n"
                "os.write(1, b'{\\\"type\\\":\\\"log\\\",\\\"values\\\":[\\\"')\n"
                "chunk = b'x' * 65536\n"
                "for _ in range(64):\n"
                "    os.write(1, chunk)\n",
            )

            with patch.dict(os.environ, self._path_environment(fake_node.parent)):
                with self.assertRaisesRegex(RuntimeError, "oversized protocol message"):
                    self._run_workflow()

    def test_bounds_unterminated_stderr_while_draining_the_pipe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workflow-stderr-") as base:
            root = Path(base)
            fake_node = self._write_fake_node(
                root,
                "import os, sys\n"
                "sys.stdin.readline()\n"
                "chunk = b'e' * 65536\n"
                "for _ in range(64):\n"
                "    os.write(2, chunk)\n",
            )

            with patch.dict(os.environ, self._path_environment(fake_node.parent)):
                with self.assertRaises(RuntimeError) as raised:
                    self._run_workflow()

        message = str(raised.exception)
        self.assertLessEqual(len(message), 20_100)
        self.assertIn("[truncated to 20000 chars", message)
        self.assertIn("Workflow bridge exited before completion", message)

    @staticmethod
    def _run_workflow() -> object:
        return run_node_workflow(
            source="return 1;",
            filename="workflow.js",
            execute_agent=lambda _request, _cancelled: {},
            cancel_event=Event(),
            cached_calls={},
            on_call_completed=lambda _request, _result, _cached: None,
        )

    @staticmethod
    def _write_fake_node(root: Path, source: str) -> Path:
        bin_dir = root / "bin"
        bin_dir.mkdir()
        fake_node = bin_dir / "node"
        fake_node.write_text(f"#!/usr/bin/env python3\n{source}", encoding="utf-8")
        fake_node.chmod(0o755)
        return fake_node

    @staticmethod
    def _path_environment(bin_dir: Path) -> dict[str, str]:
        return {"PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}


if __name__ == "__main__":
    unittest.main()
