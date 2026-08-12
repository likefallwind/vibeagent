from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent.auto_mode_management import (
    get_auto_mode_critique_report,
    parse_auto_mode_critique,
    reset_user_auto_mode_config,
)
from vibeagent.types import AssistantResponse


class CritiqueClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.messages = []

    def complete(self, messages, **_kwargs):
        self.messages.append(messages)
        return AssistantResponse(
            content=[{"type": "text", "text": json.dumps(self.payload)}],
            raw={},
        )


class AutoModeCritiqueTests(unittest.TestCase):
    def test_reviews_only_custom_classifier_rules_with_no_tools(self) -> None:
        rule = "deploy: staging deploys are always allowed"
        client = CritiqueClient(
            {
                "summary": "One rule is too broad.",
                "findings": [
                    {
                        "severity": "high",
                        "section": "allow",
                        "rule": rule,
                        "issue": "The target is ambiguous.",
                        "recommendation": "Name the exact staging namespace.",
                    }
                ],
            }
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-critique-") as base:
            report = get_auto_mode_critique_report(
                base,
                {},
                setting_sources=(),
                settings_override_json=json.dumps({"autoMode": {"allow": [rule]}}),
                create_client=lambda _env: client,
            )

        self.assertTrue(report["modelRequested"])
        self.assertEqual(report["reviewedRules"], 1)
        self.assertEqual(report["findings"][0]["severity"], "high")
        self.assertIn("untrusted data", str(client.messages[0][0].content))
        self.assertIn(rule, str(client.messages[0][1].content))

    def test_no_custom_rules_skips_model_creation(self) -> None:
        create_client = Mock(side_effect=AssertionError("provider must not be called"))
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-critique-") as base:
            report = get_auto_mode_critique_report(
                base,
                {},
                setting_sources=(),
                create_client=create_client,
            )
        self.assertFalse(report["modelRequested"])
        create_client.assert_not_called()

    def test_rejects_findings_for_rules_the_model_invented(self) -> None:
        payload = json.dumps(
            {
                "summary": "bad",
                "findings": [
                    {
                        "severity": "low",
                        "section": "allow",
                        "rule": "invented",
                        "issue": "issue",
                        "recommendation": "fix",
                    }
                ],
            }
        )
        with self.assertRaisesRegex(ValueError, "unknown custom rule"):
            parse_auto_mode_critique(payload, {"allow": ("real",)})

    def test_validates_exact_secret_bearing_rule_before_redacting_output(self) -> None:
        rule = "registry token sk-secret-value may be used internally"
        payload = json.dumps(
            {
                "summary": "One credential-shaped rule.",
                "findings": [
                    {
                        "severity": "high",
                        "section": "hard_deny",
                        "rule": rule,
                        "issue": "The rule embeds a credential.",
                        "recommendation": "Reference the credential class, not its value.",
                    }
                ],
            }
        )
        report = parse_auto_mode_critique(payload, {"hard_deny": (rule,)})
        self.assertNotIn("sk-secret-value", str(report))


class AutoModeResetTests(unittest.TestCase):
    def test_confirmation_removes_only_user_auto_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-home-") as base:
            home = Path(base)
            settings = home / ".claude/settings.json"
            settings.parent.mkdir()
            settings.write_text(
                json.dumps(
                    {
                        "model": "keep-model",
                        "autoMode": {
                            "allow": ["custom"],
                            "classifyAllShell": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            confirm = Mock(return_value="yes")
            with patch("vibeagent.auto_mode_management.user_home", return_value=home):
                report = reset_user_auto_mode_config(confirm_func=confirm)
            payload = json.loads(settings.read_text(encoding="utf-8"))

        self.assertTrue(report["changed"])
        self.assertEqual(payload, {"model": "keep-model"})
        self.assertIn("allow=1", confirm.call_args.args[0])

    def test_declining_reset_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-home-") as base:
            home = Path(base)
            settings = home / ".claude/settings.json"
            settings.parent.mkdir()
            original = '{"autoMode":{"allow":["keep"]}}\n'
            settings.write_text(original, encoding="utf-8")
            with patch("vibeagent.auto_mode_management.user_home", return_value=home):
                report = reset_user_auto_mode_config(confirm_func=lambda _prompt: "no")
            current = settings.read_text(encoding="utf-8")
        self.assertTrue(report["cancelled"])
        self.assertEqual(current, original)

    def test_detects_settings_change_during_confirmation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-home-") as base:
            home = Path(base)
            settings = home / ".claude/settings.json"
            settings.parent.mkdir()
            settings.write_text('{"autoMode":{"allow":["old"]}}', encoding="utf-8")

            def change_settings(_prompt: str) -> str:
                settings.write_text('{"autoMode":{"allow":["new", "rule"]}}', encoding="utf-8")
                return "yes"

            with patch("vibeagent.auto_mode_management.user_home", return_value=home):
                with self.assertRaisesRegex(ValueError, "changed while reset confirmation"):
                    reset_user_auto_mode_config(confirm_func=change_settings)

    def test_refuses_symlinked_user_settings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-home-") as base:
            home = Path(base)
            settings_dir = home / ".claude"
            settings_dir.mkdir()
            target = home / "target.json"
            target.write_text('{"autoMode":{"allow":["keep"]}}', encoding="utf-8")
            (settings_dir / "settings.json").symlink_to(target)
            with patch("vibeagent.auto_mode_management.user_home", return_value=home):
                with self.assertRaisesRegex(ValueError, "regular non-symlink"):
                    reset_user_auto_mode_config(yes=True)
            current = target.read_text(encoding="utf-8")
        self.assertIn("autoMode", current)


if __name__ == "__main__":
    unittest.main()
