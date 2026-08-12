import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent import run_agent
from vibeagent.cli_args import parse_args
from vibeagent.cli_one_shot_input import resolve_one_shot_code_task
from vibeagent.interactive_background import create_interactive_background_request
from vibeagent.types import AssistantResponse
from vibeagent.workspace_core import create_local_workspace
from vibeagent.workspace_prompt_commands import (
    expand_project_prompt_command,
    read_project_prompt_commands,
)
from vibeagent.workspace_skills import read_project_skill, read_project_skills


class RecordingClient:
    def __init__(self, responses):
        self.responses = responses
        self.tools = []
        self.calls = 0

    def complete(self, messages, tools=None, **kwargs):
        self.tools.append(list(tools or []))
        content = self.responses[self.calls]
        self.calls += 1
        return AssistantResponse(content=content, raw={"content": content})


class DisableSlashCommandsTests(unittest.TestCase):
    def test_parser_accepts_flag(self) -> None:
        args = parse_args(["--disable-slash-commands", "inspect"])

        self.assertTrue(args.disable_slash_commands)

    def test_one_shot_rejects_builtin_and_custom_slash_commands(self) -> None:
        for task in ("/review", "/custom argument"):
            with self.subTest(task=task), self.assertRaisesRegex(
                ValueError, "disabled by --disable-slash-commands"
            ):
                resolve_one_shot_code_task(
                    task,
                    request_mode="code",
                    project_root=Path("/project"),
                    disable_slash_commands=True,
                )

    def test_workspace_hides_commands_and_skills(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-disable-slash-") as base:
            root = Path(base)
            command = root / ".claude" / "commands" / "fix.md"
            skill = root / ".claude" / "skills" / "review" / "SKILL.md"
            command.parent.mkdir(parents=True)
            skill.parent.mkdir(parents=True)
            command.write_text("Fix $ARGUMENTS", encoding="utf-8")
            skill.write_text("---\ndescription: Review code\n---\nReview it.", encoding="utf-8")
            workspace = create_local_workspace(
                root,
                "disabled",
                disable_slash_commands=True,
            )

            self.assertEqual(read_project_prompt_commands(root, workspace=workspace)["total"], 0)
            self.assertEqual(read_project_skills(workspace)["total"], 0)
            with self.assertRaisesRegex(ValueError, "disabled by --disable-slash-commands"):
                expand_project_prompt_command(root, "/fix bug", workspace=workspace)
            with self.assertRaisesRegex(ValueError, "disabled by --disable-slash-commands"):
                read_project_skill(workspace, "review")

    def test_agent_hides_skill_tools_and_rejects_direct_call(self) -> None:
        client = RecordingClient(
            [
                [{"type": "tool_call", "id": "skill-1", "name": "Skill", "input": {"skill": "review"}}],
                [{"type": "text", "text": "Done."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-disable-slash-agent-") as base:
            root = Path(base)
            result = run_agent(
                "Inspect",
                base_dir=root,
                client=client,
                max_iterations=2,
                disable_slash_commands=True,
            )
            events = [
                json.loads(line)
                for line in (root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        for tools in client.tools:
            names = {str(tool["name"]) for tool in tools}
            self.assertTrue(names.isdisjoint({"Skill", "skill", "project_skills"}))
        self.assertTrue(any(item["type"] == "slash_commands_disabled" for item in events))
        self.assertTrue(any(item.kind == "tool_error" for item in result.observations))

    def test_background_resume_preserves_flag(self) -> None:
        request = create_interactive_background_request(
            Path("/project"),
            "run-1",
            None,
            approval_policy="ask",
            model=None,
            agent=None,
            dynamic_agent_profiles=(),
            effort=None,
            autocompact_tokens=None,
            system_prompt=None,
            append_system_prompt=None,
            additional_directories=(),
            disable_slash_commands=True,
        )

        self.assertIn("--disable-slash-commands", request.argv)


if __name__ == "__main__":
    unittest.main()
