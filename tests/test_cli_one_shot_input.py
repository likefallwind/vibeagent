import unittest

from vibeagent import cli as cli_module


class CliOneShotInputTests(unittest.TestCase):
    def test_build_one_shot_kwargs_from_args_keeps_main_mapping(self) -> None:
        args = cli_module.parse_args(
            [
                "--chat",
                "--approval",
                "allow",
                "--resume",
                "last",
                "--max-iterations",
                "7",
                "--command-timeout-ms",
                "1234",
                "explain",
                "repo",
            ]
        )

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertEqual(kwargs["task"], "explain repo")
        self.assertEqual(kwargs["request_mode"], "chat")
        self.assertEqual(kwargs["approval_policy"], "allow")
        self.assertEqual(kwargs["resume_arg"], "last")
        self.assertEqual(kwargs["max_iterations"], 7)
        self.assertEqual(kwargs["command_timeout_ms"], 1234)
        self.assertTrue(kwargs["auto_compact"])
        self.assertEqual(kwargs["permission_overrides"].rules, ())
        self.assertIs(kwargs["provider_args"], args)

        plan_args = cli_module.parse_args(["--approval", "plan", "inspect", "repo"])
        self.assertEqual(plan_args.approval, "plan")

    def test_build_one_shot_kwargs_from_args_includes_system_prompt_overrides(self) -> None:
        args = cli_module.parse_args(
            [
                "--system-prompt",
                "You are a release engineer.",
                "--append-system-prompt",
                "Prefer focused tests.",
                "inspect",
            ]
        )

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertEqual(kwargs["system_prompt"], "You are a release engineer.")
        self.assertEqual(kwargs["append_system_prompt"], "Prefer focused tests.")

    def test_build_one_shot_kwargs_from_args_includes_mcp_config_paths(self) -> None:
        args = cli_module.parse_args(["--mcp-config", "extra.mcp.json", "inspect"])

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertEqual(kwargs["mcp_config_paths"], ["extra.mcp.json"])
        self.assertFalse(kwargs["strict_mcp_config"])

    def test_build_one_shot_kwargs_from_args_includes_strict_mcp_config(self) -> None:
        args = cli_module.parse_args(["--mcp-config", "extra.mcp.json", "--strict-mcp-config", "inspect"])

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertEqual(kwargs["mcp_config_paths"], ["extra.mcp.json"])
        self.assertTrue(kwargs["strict_mcp_config"])

    def test_build_one_shot_kwargs_from_args_includes_no_auto_compact(self) -> None:
        args = cli_module.parse_args(["--no-auto-compact", "inspect"])

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertFalse(kwargs["auto_compact"])

    def test_cli_compat_aliases_map_to_existing_one_shot_fields(self) -> None:
        args = cli_module.parse_args(
            [
                "-p",
                "-c",
                "--permission-mode",
                "plan",
                "--max-turns",
                "3",
                "inspect",
                "repo",
            ]
        )

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertTrue(args.print_mode)
        self.assertTrue(args.continue_latest)
        self.assertEqual(args.resume, "")
        self.assertTrue(args.resume_from_continue)
        self.assertEqual(kwargs["approval_policy"], "plan")
        self.assertEqual(kwargs["resume_arg"], "")
        self.assertEqual(kwargs["max_iterations"], 3)
        self.assertTrue(kwargs["print_mode"])

    def test_cli_continue_long_alias_maps_to_latest_resume_context(self) -> None:
        args = cli_module.parse_args(["--continue", "inspect", "repo"])

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertTrue(args.continue_latest)
        self.assertEqual(args.resume, "")
        self.assertTrue(args.resume_from_continue)
        self.assertEqual(kwargs["resume_arg"], "")
        self.assertIsNone(cli_module.validate_cli_args(args))

    def test_cli_permission_mode_accepts_claude_values(self) -> None:
        cases = [
            ("default", "ask"),
            ("acceptEdits", "ask"),
            ("bypassPermissions", "allow"),
            ("plan", "plan"),
        ]

        for value, expected in cases:
            with self.subTest(value=value):
                args = cli_module.parse_args(["--permission-mode", value, "inspect"])
                kwargs = cli_module.build_one_shot_kwargs_from_args(args)

                self.assertEqual(args.approval, expected)
                self.assertEqual(kwargs["approval_policy"], expected)
                self.assertIsNone(cli_module.validate_cli_args(args))

                expected_rules = ["Edit", "NotebookEdit"] if value == "acceptEdits" else []
                self.assertEqual([rule.raw for rule in kwargs["permission_overrides"].rules], expected_rules)

    def test_cli_dangerously_skip_permissions_maps_to_allow_for_code_tasks(self) -> None:
        args = cli_module.parse_args(["--dangerously-skip-permissions", "inspect", "repo"])

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertTrue(args.dangerously_skip_permissions)
        self.assertEqual(args.approval, "allow")
        self.assertEqual(kwargs["approval_policy"], "allow")
        self.assertIsNone(cli_module.validate_cli_args(args))

    def test_cli_session_id_alias_maps_to_resume_arg(self) -> None:
        args = cli_module.parse_args(["--session-id", "run-1", "continue"])

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertEqual(args.session_id, "run-1")
        self.assertEqual(kwargs["resume_arg"], "run-1")

    def test_build_one_shot_kwargs_from_args_includes_permission_overrides(self) -> None:
        args = cli_module.parse_args(
            [
                "--allowedTools",
                "Read",
                "--allowed-tools",
                "Bash(git diff:*)",
                "--disallowedTools",
                "Edit(src/**)",
                "inspect",
            ]
        )

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)
        permissions = kwargs["permission_overrides"]

        self.assertEqual([rule.effect for rule in permissions.rules], ["allow", "allow", "deny"])
        self.assertEqual([rule.raw for rule in permissions.rules], ["Read", "Bash(git diff:*)", "Edit(src/**)"])
        self.assertTrue(permissions.trusted_allow_sources)

    def test_accept_edits_permission_mode_adds_edit_permission_overrides(self) -> None:
        args = cli_module.parse_args(["--permission-mode", "acceptEdits", "inspect"])

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)
        permissions = kwargs["permission_overrides"]

        self.assertEqual(kwargs["approval_policy"], "ask")
        self.assertEqual([rule.effect for rule in permissions.rules], ["allow", "allow"])
        self.assertEqual([rule.raw for rule in permissions.rules], ["Edit", "NotebookEdit"])
        self.assertEqual(
            [rule.source for rule in permissions.rules],
            ["<cli --permission-mode acceptEdits>", "<cli --permission-mode acceptEdits>"],
        )
        self.assertEqual(permissions.trusted_allow_sources, ("<cli --permission-mode acceptEdits>",))


if __name__ == "__main__":
    unittest.main()
