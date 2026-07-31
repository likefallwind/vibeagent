import subprocess
import tempfile
import unittest
from pathlib import Path

from vibeagent.commands import (
    format_check_suggested_checks_report_text,
    format_checks_report_text,
    format_run_suggested_checks_report_text,
    get_check_suggested_checks_report,
    get_check_suggested_checks_text,
    get_checks_report,
    get_checks_text,
    get_run_suggested_checks_report,
    get_run_suggested_checks_text,
)


class SuggestedChecksCommandTests(unittest.TestCase):
    def test_get_checks_text_reports_suggested_verification_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js","build":"vite build","dev":"vite"}}\n', encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
            (root / "pkg").mkdir()
            (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")

            text = get_checks_text(root)
            limited = get_checks_text(root, max_checks=1)

        self.assertIn("Checks:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("suggestedChecks:", text)
        self.assertIn("changedFiles:", text)
        self.assertIn("commands:", text)
        self.assertIn("npm run test", text)
        self.assertIn("suggestedChecks: 1/", limited)
        self.assertIn("truncated: yes", limited)

        with self.assertRaisesRegex(ValueError, "max_checks must be at most 100"):
            get_checks_text(root, max_checks=101)
        self.assertIn("npm run build", text)
        self.assertIn("python -m unittest discover -s tests", text)
        self.assertIn("python -m compileall -q pkg", text)

    def test_get_checks_report_returns_structured_suggestions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js","build":"vite build","dev":"vite"}}\n', encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
            (root / "pkg").mkdir()
            (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")

            report = get_checks_report(root, max_checks=10)
            rendered = format_checks_report_text(report)

        self.assertEqual(report["projectRoot"], str(root.resolve()))
        suggested = report["suggestedChecks"]
        self.assertIsInstance(suggested, dict)
        self.assertLessEqual(suggested["shown"], suggested["total"])
        self.assertFalse(suggested["truncated"])
        self.assertIsInstance(suggested["commands"], list)
        commands = [item["command"] for item in suggested["commands"] if isinstance(item, dict)]
        self.assertIn("npm run test", commands)
        self.assertIn("python -m unittest discover -s tests", commands)
        self.assertIsInstance(report["changedFiles"], list)
        self.assertIsInstance(report["message"], str)
        self.assertIn("Checks:", rendered)
        self.assertIn(f"projectRoot: {root.resolve()}", rendered)
        self.assertIn("suggestedChecks:", rendered)
        self.assertIn("npm run test", rendered)
        self.assertIn("python -m unittest discover -s tests", rendered)

    def test_get_check_suggested_checks_text_preflights_suggested_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text(
                "import unittest\n\nclass AppTests(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            text = get_check_suggested_checks_text(root, "1")
            named_text = get_check_suggested_checks_text(root, "--max-checks=1")
            invalid = get_check_suggested_checks_text(root, "11")

        self.assertIn("Check suggested checks:", text)
        self.assertIn("Check suggested checks:", named_text)
        self.assertIn("ok: yes", text)
        self.assertIn("commands: 1/", text)
        self.assertIn("python -m unittest discover -s tests", text)
        self.assertIn("max must be at most 10", invalid)

    def test_check_suggested_checks_report_returns_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text(
                "import unittest\n\nclass AppTests(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            report = get_check_suggested_checks_report(root, "1")
            usage = get_check_suggested_checks_report(root, "11")
            rendered = format_check_suggested_checks_report_text(report)

        self.assertEqual(report["projectRoot"], str(root.resolve()))
        self.assertTrue(report["ok"])
        self.assertEqual(report["commands"]["shown"], 1)
        self.assertEqual(report["suggestedChecks"]["shown"], 1)
        self.assertEqual(report["checks"][0]["command"], "python -m unittest discover -s tests")
        self.assertTrue(report["checks"][0]["ok"])
        self.assertIn("Check suggested checks:", rendered)
        self.assertEqual(
            format_check_suggested_checks_report_text(usage),
            "Usage: /check-suggested-checks [max|--max-checks N]\nError: max must be at most 10.",
        )

    def test_check_suggested_checks_report_is_not_ok_when_truncated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "pkg").mkdir()
            (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text(
                "import unittest\n\nclass AppTests(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            report = get_check_suggested_checks_report(root, "1")
            rendered = format_check_suggested_checks_report_text(report)

        self.assertFalse(report["ok"])
        self.assertTrue(report["truncated"])
        self.assertEqual(report["commands"]["shown"], 1)
        self.assertGreater(report["commands"]["total"], 1)
        self.assertIn("ok: no", rendered)
        self.assertIn("truncated: yes", rendered)
        self.assertIn("incomplete", rendered)

    def test_get_run_suggested_checks_text_runs_suggested_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text(
                "import unittest\n\nclass AppTests(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            text = get_run_suggested_checks_text(root, "1", timeout_ms=10_000, max_output_chars=2_000)
            named_text = get_run_suggested_checks_text(root, "--max-checks=1", timeout_ms=10_000, max_output_chars=2_000)

        self.assertIn("Run suggested checks:", text)
        self.assertIn("Run suggested checks:", named_text)
        self.assertIn("suggestedChecks:", text)
        self.assertIn("command: python -m unittest discover -s tests", text)
        self.assertIn("cwd: .", text)
        self.assertIn("source:", text)
        self.assertIn("available: yes", text)
        self.assertIn("reason:", text)
        self.assertIn("ok: yes", text)
        self.assertIn("ran: 1", text)
        self.assertIn("python -m unittest discover -s tests", text)
        self.assertIn("exitCode: 0", text)

    def test_run_suggested_checks_report_returns_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text(
                "import unittest\n\nclass AppTests(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            report = get_run_suggested_checks_report(root, "1", timeout_ms=10_000, max_output_chars=2_000)
            named_report = get_run_suggested_checks_report(root, "--max-checks 1", timeout_ms=10_000, max_output_chars=2_000)
            invalid_report = get_run_suggested_checks_report(root, "--max-checks 0", timeout_ms=10_000, max_output_chars=2_000)
            rendered = format_run_suggested_checks_report_text(report)

        self.assertTrue(report["ok"])
        self.assertTrue(named_report["ok"])
        self.assertEqual(named_report["ran"], 1)
        self.assertEqual(
            format_run_suggested_checks_report_text(invalid_report),
            "Usage: /run-suggested-checks [max|--max-checks N]\nError: max must be at least 1.",
        )
        self.assertEqual(report["suggestedChecks"]["shown"], 1)
        self.assertEqual(report["ran"], 1)
        self.assertFalse(report["stoppedEarly"])
        self.assertEqual(report["selectedCommandsNotRun"], {"count": 0, "commands": []})
        self.assertIsInstance(report["durationMs"], int)
        self.assertGreaterEqual(report["durationMs"], report["results"][0]["durationMs"])
        self.assertEqual(report["results"][0]["command"], "python -m unittest discover -s tests")
        self.assertEqual(report["results"][0]["exitCode"], 0)
        self.assertIn("Run suggested checks:", rendered)
        self.assertIn("suggestedChecks:", rendered)
        self.assertIn("command: python -m unittest discover -s tests", rendered)
        self.assertIn("cwd: .", rendered)
        self.assertIn("source:", rendered)
        self.assertIn("available: yes", rendered)
        self.assertIn("reason:", rendered)
        self.assertIn("durationMs:", rendered)
        self.assertIn("results:", rendered)

    def test_run_suggested_checks_report_is_not_ok_when_truncated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "pkg").mkdir()
            (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text(
                "import unittest\n\nclass AppTests(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            report = get_run_suggested_checks_report(root, "1", timeout_ms=10_000, max_output_chars=2_000)
            rendered = format_run_suggested_checks_report_text(report)

        self.assertFalse(report["ok"])
        self.assertTrue(report["truncated"])
        self.assertEqual(report["ran"], 1)
        self.assertGreater(report["suggestedChecks"]["total"], 1)
        self.assertIn("ok: no", rendered)
        self.assertIn("truncated: yes", rendered)
        self.assertIn("incomplete", rendered)

    def test_run_suggested_checks_rendered_report_lists_not_run_commands(self) -> None:
        rendered = format_run_suggested_checks_report_text(
            {
                "projectRoot": "/repo",
                "ok": False,
                "clean": False,
                "suggestedChecks": {
                    "shown": 2,
                    "total": 2,
                    "commands": [
                        {
                            "command": "python -m unittest tests.test_agent",
                            "cwd": ".",
                            "source": "tests",
                            "available": True,
                            "missingTool": None,
                            "reason": "unit tests",
                        }
                    ],
                },
                "selectedCommandsNotRun": {
                    "count": 1,
                    "commands": [
                        {
                            "command": "npm test",
                            "cwd": "web",
                            "source": "package.json",
                            "available": True,
                            "missingTool": None,
                            "reason": "project test script",
                        },
                    ],
                },
                "ran": 1,
                "skippedUnavailable": 0,
                "truncated": False,
                "stopOnFailure": True,
                "stoppedEarly": True,
                "durationMs": 10,
                "results": [
                    {
                        "index": 1,
                        "command": "python -m unittest tests.test_agent",
                        "cwd": ".",
                        "ok": False,
                        "clean": False,
                        "exitCode": 1,
                        "timedOut": False,
                        "signal": None,
                        "timeoutMs": 1000,
                        "durationMs": 10,
                        "maxOutputChars": 2000,
                        "stdoutTruncated": False,
                        "stderrTruncated": False,
                        "stdout": "",
                        "stderr": "AssertionError\n",
                        "analysis": {},
                    }
                ],
                "message": "Suggested checks failed.",
            }
        )

        self.assertIn("stoppedEarly: yes", rendered)
        self.assertIn("selectedCommandsNotRun: 1", rendered)
        self.assertIn("command: npm test", rendered)
        self.assertIn("cwd: web", rendered)

    def test_get_run_suggested_checks_text_can_extract_output_contexts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text(
                "import unittest\n\nclass AppTests(unittest.TestCase):\n    def test_ok(self):\n        print('src/app.py:2:5: note')\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            text = get_run_suggested_checks_text(
                root,
                "1",
                timeout_ms=10_000,
                max_output_chars=2_000,
                extract_output_contexts=True,
                context_lines=0,
                max_bytes_per_context=1000,
            )

        self.assertIn("Run suggested checks:", text)
        self.assertIn("outputContexts: 1/1", text)
        self.assertIn("clean: no", text)
        self.assertIn("src/app.py:2:5 [src/app.py:2:5]", text)
        self.assertIn("2: Two", text)
