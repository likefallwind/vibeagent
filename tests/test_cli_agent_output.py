import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent import AgentResult
from vibeagent.cli import main, print_agent_result
from vibeagent.types import TaskStep


class CliAgentOutputTests(unittest.TestCase):
    def test_main_prints_only_final_agent_message_for_code_tasks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="这是最终回复。",
                run_dir=Path(base),
                run_id="test-run",
                iterations=3,
                observations=[],
                steps=[
                    TaskStep(
                        id=1,
                        label="List files .",
                        action_type="list_files",
                        target=".",
                        status="completed",
                        message="Found 0 file(s).",
                    )
                ],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["现在用的什么 模型", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("这是最终回复。", output)
        self.assertNotIn("[thinking]", output)
        self.assertNotIn("Success", output)
        self.assertNotIn("Project directory:", output)
        self.assertNotIn("Iterations:", output)
        self.assertNotIn("Steps:", output)
        self.assertNotIn("List files .", output)
        self.assertNotIn("logger", run_agent.call_args.kwargs)

    def test_print_agent_result_shows_completion_warnings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="Done.",
                run_dir=Path(base),
                run_id="test-run",
                iterations=1,
                observations=[],
                steps=[],
                completion_ready=False,
                completion_blockers=["Final review did not report ready."],
                completion_warnings=["Project changes completed without a final_review observation."],
                verification_checks=["python -m unittest discover -s tests"],
                pending_verification_checks=["npm test"],
                failed_verification_checks=["npm test (exit=1)"],
                latest_completion_blockers=["Latest attempt still has pending verification."],
                latest_completion_pending_verification_checks=["npm run lint"],
                latest_completion_failed_verification_checks=["npm run build (exit=2)"],
                latest_completion_final_review_issues=["Changed Python files have syntax errors."],
                latest_completion_final_review_changed_files=["M app.py"],
                latest_completion_tool_errors=["read_file: Tool execution failed: boom"],
                latest_completion_checkpoint_failures=["checkpoint_create: git diff failed."],
                latest_completion_active_background_processes=["bg-1: pid=123, cwd=web, command=npm run dev"],
                latest_completion_denied_approvals=["write_file note.txt: denied"],
                final_review_changed_files=["M app.py", "A tests/test_app.py"],
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                print_agent_result(result)

        self.assertIn("Done.", stdout.getvalue())
        self.assertIn("Completion blockers:", stdout.getvalue())
        self.assertIn("Final review did not report ready.", stdout.getvalue())
        self.assertIn("Warnings:", stdout.getvalue())
        self.assertIn("Project changes completed without a final_review observation.", stdout.getvalue())
        self.assertIn("Changed files:", stdout.getvalue())
        self.assertIn("M app.py", stdout.getvalue())
        self.assertIn("A tests/test_app.py", stdout.getvalue())
        self.assertIn("Verified:", stdout.getvalue())
        self.assertIn("python -m unittest discover -s tests", stdout.getvalue())
        self.assertIn("Pending checks:", stdout.getvalue())
        self.assertIn("npm test", stdout.getvalue())
        self.assertIn("Failed checks:", stdout.getvalue())
        self.assertIn("npm test (exit=1)", stdout.getvalue())
        self.assertIn("Latest completion blockers:", stdout.getvalue())
        self.assertIn("Latest attempt still has pending verification.", stdout.getvalue())
        self.assertIn("Latest completion pending checks:", stdout.getvalue())
        self.assertIn("npm run lint", stdout.getvalue())
        self.assertIn("Latest completion failed checks:", stdout.getvalue())
        self.assertIn("npm run build (exit=2)", stdout.getvalue())
        self.assertIn("Latest final review issues:", stdout.getvalue())
        self.assertIn("Changed Python files have syntax errors.", stdout.getvalue())
        self.assertIn("Latest final review changed files:", stdout.getvalue())
        self.assertIn("M app.py", stdout.getvalue())
        self.assertIn("Latest tool errors:", stdout.getvalue())
        self.assertIn("read_file: Tool execution failed: boom", stdout.getvalue())
        self.assertIn("Latest checkpoint failures:", stdout.getvalue())
        self.assertIn("checkpoint_create: git diff failed.", stdout.getvalue())
        self.assertIn("Latest active processes:", stdout.getvalue())
        self.assertIn("bg-1: pid=123, cwd=web, command=npm run dev", stdout.getvalue())
        self.assertIn("Latest denied approvals:", stdout.getvalue())
        self.assertIn("write_file note.txt: denied", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
