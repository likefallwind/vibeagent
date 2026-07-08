import unittest

from vibeagent import command_safety, command_safety_high_risk


class CommandSafetyHighRiskTests(unittest.TestCase):
    def test_command_safety_reexports_high_risk_classifier(self) -> None:
        self.assertIs(
            command_safety.command_invokes_high_risk_executable,
            command_safety_high_risk.command_invokes_high_risk_executable,
        )


if __name__ == "__main__":
    unittest.main()
