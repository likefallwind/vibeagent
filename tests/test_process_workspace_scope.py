from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.process_io_runtime import (
    check_write_background_process,
    read_background_process,
    wait_background_process,
)
from vibeagent.process_runtime import start_background_command
from vibeagent.process_stop_runtime import (
    check_stop_background_process,
    list_background_processes,
    stop_all_background_processes,
    stop_background_process,
)
from vibeagent.workspace import create_run_workspace


class ProcessWorkspaceScopeTests(unittest.TestCase):
    def test_in_memory_processes_are_private_to_their_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-process-scope-") as base:
            owner = create_run_workspace(Path(base) / "owner", "owner-session")
            outsider = create_run_workspace(Path(base) / "outsider", "outsider-session")
            started = start_background_command(owner, "python3 -c 'import time; time.sleep(10)'")
            self.assertTrue(started.ok, started.message)

            try:
                self.assertEqual(list_background_processes(outsider.root).processes, [])
                self.assertFalse(read_background_process(outsider.root, started.process_id).ok)
                self.assertFalse(wait_background_process(outsider.root, started.process_id, timeout_ms=1).ok)
                self.assertFalse(check_write_background_process(outsider.root, started.process_id, "x").ok)
                self.assertFalse(check_stop_background_process(outsider.root, started.process_id).ok)
                self.assertFalse(stop_background_process(outsider.root, started.process_id).ok)
                self.assertEqual(stop_all_background_processes(outsider.root).stopped, [])

                owner_processes = list_background_processes(owner.root).processes
                self.assertEqual([process.process_id for process in owner_processes], [started.process_id])
                self.assertTrue(owner_processes[0].running)
            finally:
                stop_background_process(owner.root, started.process_id)


if __name__ == "__main__":
    unittest.main()
