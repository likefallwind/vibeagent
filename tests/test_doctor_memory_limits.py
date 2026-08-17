import subprocess
import unittest
from unittest.mock import patch

from vibeagent.cli_exit_predicates import has_local_diagnostic_error
from vibeagent.doctor_memory_limits import get_memory_limits_doctor_report
from vibeagent.workflow_doctor_commands import format_doctor_report_text


class DoctorMemoryLimitsTests(unittest.TestCase):
    def test_reports_configured_limits_when_user_systemd_is_reachable(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with (
            patch("vibeagent.doctor_memory_limits.sys.platform", "linux"),
            patch(
                "vibeagent.doctor_memory_limits.shutil.which",
                side_effect=lambda name, path=None: f"/usr/bin/{name}",
            ),
            patch(
                "vibeagent.doctor_memory_limits.subprocess.run",
                return_value=completed,
            ) as run,
        ):
            report = get_memory_limits_doctor_report(
                {
                    "PATH": "/usr/bin",
                    "CLAUDE_CODE_TOOL_MEMORY_LIMIT": "2GiB",
                    "VIBEAGENT_BACKGROUND_AGENT_MEMORY_LIMIT": "512M",
                }
            )

        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "ready")
        self.assertTrue(report["support"]["userManager"])
        self.assertEqual(report["toolCommands"]["limitBytes"], 2 * 1024**3)
        self.assertEqual(report["toolCommands"]["limit"], "2 GiB")
        self.assertEqual(report["backgroundAgents"]["limitBytes"], 512 * 1024**2)
        run.assert_called_once()
        self.assertEqual(
            run.call_args.args[0],
            ["/usr/bin/systemctl", "--user", "show-environment"],
        )
        self.assertIs(run.call_args.kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(run.call_args.kwargs["timeout"], 2.0)

    def test_unavailable_support_is_informational_when_limits_are_unconfigured(self) -> None:
        with (
            patch("vibeagent.doctor_memory_limits.sys.platform", "linux"),
            patch("vibeagent.doctor_memory_limits.shutil.which", return_value=None),
            patch("vibeagent.doctor_memory_limits.subprocess.run") as run,
        ):
            report = get_memory_limits_doctor_report({"PATH": "/missing"})

        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "not configured")
        self.assertFalse(report["support"]["ready"])
        run.assert_not_called()

    def test_configured_limit_fails_when_user_systemd_is_unreachable(self) -> None:
        completed = subprocess.CompletedProcess(
            [],
            1,
            stdout="",
            stderr="Failed to connect to bus: unavailable\nextra detail",
        )
        with (
            patch("vibeagent.doctor_memory_limits.sys.platform", "linux"),
            patch(
                "vibeagent.doctor_memory_limits.shutil.which",
                side_effect=lambda name, path=None: f"/usr/bin/{name}",
            ),
            patch(
                "vibeagent.doctor_memory_limits.subprocess.run",
                return_value=completed,
            ),
        ):
            report = get_memory_limits_doctor_report(
                {"CLAUDE_CODE_TOOL_MEMORY_LIMIT": "1GiB"}
            )

        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(
            report["support"]["error"],
            "Failed to connect to bus: unavailable extra detail",
        )

    def test_invalid_values_are_reported_without_echoing_unrelated_environment(self) -> None:
        with (
            patch("vibeagent.doctor_memory_limits.sys.platform", "linux"),
            patch("vibeagent.doctor_memory_limits.shutil.which", return_value=None),
        ):
            report = get_memory_limits_doctor_report(
                {
                    "CLAUDE_CODE_TOOL_MEMORY_LIMIT": "huge",
                    "VIBEAGENT_BACKGROUND_AGENT_MEMORY_LIMIT": "-1",
                    "MINIMAX_API_KEY": "secret-key",
                }
            )

        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "invalid")
        self.assertFalse(report["toolCommands"]["valid"])
        self.assertFalse(report["backgroundAgents"]["valid"])
        self.assertNotIn("secret-key", str(report))

    def test_explicitly_disabled_background_limit_does_not_require_systemd(self) -> None:
        with (
            patch("vibeagent.doctor_memory_limits.sys.platform", "darwin"),
            patch("vibeagent.doctor_memory_limits.shutil.which", return_value=None),
        ):
            report = get_memory_limits_doctor_report(
                {"VIBEAGENT_BACKGROUND_AGENT_MEMORY_LIMIT": "off"}
            )

        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "disabled")
        self.assertFalse(report["backgroundAgents"]["enabled"])

    def test_text_and_exit_predicate_surface_unavailable_configured_limit(self) -> None:
        report = {
            "memoryLimits": {
                "ok": False,
                "status": "unavailable",
                "support": {
                    "ready": False,
                    "platform": "linux",
                    "systemdRun": True,
                    "systemctl": True,
                    "userManager": False,
                    "error": "User systemd manager is unavailable.",
                },
                "toolCommands": {
                    "environment": "CLAUDE_CODE_TOOL_MEMORY_LIMIT",
                    "configured": True,
                    "enabled": True,
                    "valid": True,
                    "limitBytes": 2 * 1024**3,
                    "limit": "2 GiB",
                },
                "backgroundAgents": {
                    "environment": "VIBEAGENT_BACKGROUND_AGENT_MEMORY_LIMIT",
                    "configured": False,
                    "enabled": False,
                    "valid": True,
                    "limitBytes": None,
                    "limit": None,
                },
            }
        }

        text = format_doctor_report_text(report)

        self.assertIn("memoryLimits: unavailable", text)
        self.assertIn("support: unavailable", text)
        self.assertIn("toolCommands: 2 GiB (CLAUDE_CODE_TOOL_MEMORY_LIMIT)", text)
        self.assertTrue(has_local_diagnostic_error(text))


if __name__ == "__main__":
    unittest.main()
