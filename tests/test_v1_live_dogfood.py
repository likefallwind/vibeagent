from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "live_dogfood_v1.py"
SPEC = importlib.util.spec_from_file_location("live_dogfood_v1", SCRIPT_PATH)
assert SPEC is not None
live_dogfood_v1 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = live_dogfood_v1
SPEC.loader.exec_module(live_dogfood_v1)


class V1LiveDogfoodScriptTests(unittest.TestCase):
    def test_prepare_repo_creates_broken_calculator_and_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-live-dogfood-script-") as base:
            root = Path(base) / "repo"

            live_dogfood_v1.prepare_repo(root)
            command = live_dogfood_v1.dogfood_command(root)

            self.assertEqual(command[:3], ["python3", "-m", "vibeagent"])
            self.assertIn("--approval", command)
            self.assertIn("ask", command)
            self.assertIn("inspect this repo, fix the failing test, verify, review, and commit", command)
            self.assertIn("return left - right", (root / "calc.py").read_text(encoding="utf-8"))

    def test_audit_repo_fails_before_repair_and_passes_after_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-live-dogfood-audit-") as base:
            root = Path(base) / "repo"
            live_dogfood_v1.prepare_repo(root)

            before = live_dogfood_v1.audit_repo(root, run_id=None)
            (root / "calc.py").write_text("def add(left, right):\n    return left + right\n", encoding="utf-8")
            subprocess.run(["git", "add", "calc.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "fix calculator"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            after = live_dogfood_v1.audit_repo(root, run_id=None)

            self.assertFalse(all(check.ok for check in before))
            self.assertTrue(all(check.ok for check in after))


if __name__ == "__main__":
    unittest.main()
