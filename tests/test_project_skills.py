import tempfile
import unittest
from pathlib import Path

from tests.user_home_test_case import IsolatedUserHomeTestCase
from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.agent_tool_registry import initial_agent_tool_names
from vibeagent.prompts import build_messages, format_observations
from vibeagent.types import ProjectOverviewAction, ProjectSkillsAction, SkillAction, ToolSearchAction
from vibeagent.workspace import create_run_workspace, format_project_skill_catalog, read_project_skill, read_project_skills
from vibeagent.workspace_prompt_commands import expand_project_prompt_command


def _write_skill(root: Path, base: str, name: str, description: str, body: str) -> Path:
    path = root / base / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n", encoding="utf-8")
    return path


class ProjectSkillWorkspaceTests(IsolatedUserHomeTestCase):
    def test_discovers_metadata_then_loads_one_skill_on_demand(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-skills-") as base:
            root = Path(base)
            _write_skill(root, ".claude/skills", "release-check", '"Validate releases safely"', "Run focused tests first.")
            workspace = create_run_workspace(root, "run-1")

            catalog = read_project_skills(workspace)
            loaded = read_project_skill(workspace, "release-check")

        self.assertEqual(catalog["total"], 1)
        self.assertEqual(catalog["invalid"], 0)
        self.assertEqual(catalog["skills"][0]["description"], "Validate releases safely")
        self.assertNotIn("content", catalog["skills"][0])
        self.assertIn("Run focused tests first.", loaded["content"])
        self.assertEqual(loaded["source"], "claude")
        self.assertFalse(loaded["truncated"])

    def test_duplicate_names_are_unavailable_instead_of_using_precedence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-skills-") as base:
            root = Path(base)
            _write_skill(root, ".claude/skills", "review", "Claude review", "Claude body")
            _write_skill(root, ".agents/skills", "review", "Agent review", "Agent body")
            workspace = create_run_workspace(root, "run-1")

            catalog = read_project_skills(workspace)
            with self.assertRaisesRegex(ValueError, "Duplicate skill name"):
                read_project_skill(workspace, "review")

        self.assertEqual(catalog["total"], 2)
        self.assertEqual(catalog["invalid"], 2)
        self.assertTrue(all(not item["available"] for item in catalog["skills"]))

    def test_discovers_and_loads_directory_qualified_nested_skills(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-skills-") as base:
            root = Path(base)
            _write_skill(root, ".claude/skills", "deploy", "Deploy all apps", "ROOT_DEPLOY")
            _write_skill(
                root,
                "apps/web/.claude/skills",
                "deploy",
                "Deploy the web app",
                "WEB_DEPLOY",
            )
            _write_skill(
                root,
                "packages/api/.claude/skills",
                "deploy",
                "Deploy the API",
                "API_DEPLOY",
            )
            workspace = create_run_workspace(root, "nested-skills")

            catalog = read_project_skills(workspace)
            root_skill = read_project_skill(workspace, "deploy")
            bounded_root_skill = read_project_skill(workspace, "deploy", max_bytes=200)
            web_skill = read_project_skill(workspace, "apps/web:deploy")
            api_skill = read_project_skill(workspace, "packages/api:deploy")
            invoked = expand_project_prompt_command(root, "/apps/web:deploy production")

        self.assertEqual(
            [item["name"] for item in catalog["skills"]],
            ["apps/web:deploy", "deploy", "packages/api:deploy"],
        )
        self.assertEqual(web_skill["source"], "nested_claude")
        self.assertEqual(web_skill["path"], "apps/web/.claude/skills/deploy/SKILL.md")
        self.assertIn("WEB_DEPLOY", web_skill["content"])
        self.assertIn("API_DEPLOY", api_skill["content"])
        self.assertIn("apps/web:deploy", root_skill["content"])
        self.assertIn("packages/api:deploy", root_skill["content"])
        self.assertLessEqual(len(bounded_root_skill["content"].encode("utf-8")), 200)
        self.assertTrue(bounded_root_skill["truncated"])
        self.assertEqual(invoked["name"], "apps/web:deploy")
        self.assertEqual(invoked["arguments"], "production")
        self.assertIn("WEB_DEPLOY", invoked["prompt"])

    def test_nested_skill_names_and_paths_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-skills-") as base:
            root = Path(base) / "project"
            outside = Path(base) / "outside"
            root.mkdir()
            outside.mkdir()
            _write_skill(outside, ".claude/skills", "escaped", "External", "EXTERNAL_BODY")
            nested_link = root / "apps/web/.claude"
            nested_link.parent.mkdir(parents=True)
            nested_link.symlink_to(outside / ".claude", target_is_directory=True)
            _write_skill(
                root,
                "apps:invalid/.claude/skills",
                "deploy",
                "Invalid scope",
                "INVALID_SCOPE_BODY",
            )
            workspace = create_run_workspace(root, "nested-symlink")

            catalog = read_project_skills(workspace)

            for name in ("../apps:deploy", "apps//web:deploy", "apps/web/:deploy"):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, "directory namespace"):
                    read_project_skill(workspace, name)

        self.assertEqual(len(catalog["skills"]), 1)
        self.assertFalse(catalog["skills"][0]["available"])
        self.assertIn("scope is invalid", catalog["skills"][0]["message"])

    def test_rejects_symlinked_skill_and_invalid_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-skills-") as base:
            root = Path(base)
            external = root / "outside.md"
            external.write_text("---\nname: linked\ndescription: escaped\n---\nsecret\n", encoding="utf-8")
            linked = root / ".agents/skills/linked/SKILL.md"
            linked.parent.mkdir(parents=True)
            linked.symlink_to(external)
            missing = root / ".claude/skills/missing/SKILL.md"
            missing.parent.mkdir(parents=True)
            missing.write_text("# No frontmatter description\n", encoding="utf-8")
            workspace = create_run_workspace(root, "run-1")

            catalog = read_project_skills(workspace)

        messages = {item["name"]: item["message"] for item in catalog["skills"]}
        self.assertIn("symbolic link", messages["linked"])
        self.assertIn("requires non-empty name and description", messages["missing"])
        self.assertEqual(catalog["invalid"], 2)

    def test_loaded_skill_text_is_byte_bounded(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-skills-") as base:
            root = Path(base)
            _write_skill(root, ".agents/skills", "bounded", "Bounded content", "x" * 1000)
            workspace = create_run_workspace(root, "run-1")

            loaded = read_project_skill(workspace, "bounded", max_bytes=200)

        self.assertLessEqual(len(loaded["content"].encode("utf-8")), 200)
        self.assertTrue(loaded["truncated"])
        self.assertEqual(loaded["max_bytes"], 200)

    def test_catalog_and_project_snapshot_do_not_include_skill_body(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-skills-") as base:
            root = Path(base)
            _write_skill(root, ".claude/skills", "deploy", "Deploy the service", "PRIVATE_SKILL_BODY")
            workspace = create_run_workspace(root, "run-1")

            catalog = format_project_skill_catalog(workspace)
            messages = build_messages("Deploy", workspace)

        self.assertIn("deploy: Deploy the service", catalog or "")
        prompt = str(messages[1].content)
        self.assertIn("deploy: Deploy the service", prompt)
        self.assertNotIn("PRIVATE_SKILL_BODY", prompt)


class ProjectSkillActionTests(IsolatedUserHomeTestCase):
    def test_actions_parse_and_execute_structured_observations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-skills-") as base:
            root = Path(base)
            _write_skill(root, ".agents/skills", "testing", "Run project tests", "Use unittest.")
            workspace = create_run_workspace(root, "run-1")

            list_action = parse_tool_action("project_skills", {"max_skills": 5})
            load_action = parse_tool_action("skill", {"name": "testing", "max_bytes": 500})
            listed = execute_action(workspace, list_action)
            loaded = execute_action(workspace, load_action)

        self.assertIsInstance(list_action, ProjectSkillsAction)
        self.assertIsInstance(load_action, SkillAction)
        self.assertEqual(listed.kind, "project_skills")
        self.assertTrue(listed.ok)
        self.assertEqual(listed.skills[0].name, "testing")
        self.assertEqual(loaded.kind, "skill")
        self.assertTrue(loaded.ok)
        self.assertIn("Use unittest.", loaded.content)

    def test_claude_aliases_search_and_load_skill_with_arguments(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-skills-") as base:
            root = Path(base)
            _write_skill(root, ".claude/skills", "release-check", "Validate releases", "Run the release gate.")
            workspace = create_run_workspace(root, "run-1")

            search_action = parse_tool_action("ToolSearch", {"query": "project skill", "max_results": 5})
            search_result = execute_action(workspace, search_action)
            load_action = parse_tool_action(
                "Skill",
                {"skill": "release-check", "args": "Validate version 1.1", "max_bytes": 500},
            )
            loaded = execute_action(workspace, load_action)

        self.assertEqual(
            search_action,
            ToolSearchAction(type="tool_search", query="project skill", max_matches=5),
        )
        self.assertTrue(search_result.ok)
        self.assertIn("skill", [match["name"] for match in search_result.matches])
        self.assertEqual(
            load_action,
            SkillAction(
                type="skill",
                name="release-check",
                max_bytes=500,
                arguments="Validate version 1.1",
            ),
        )
        self.assertEqual(loaded.arguments, "Validate version 1.1")
        formatted = format_observations([loaded])
        self.assertIn("arguments: Validate version 1.1", formatted)
        self.assertIn("Run the release gate.", formatted)

    def test_skill_tool_loads_directory_qualified_nested_skill(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-skills-") as base:
            root = Path(base)
            _write_skill(
                root,
                "apps/web/.claude/skills",
                "testing",
                "Test the web app",
                "Run web integration tests.",
            )
            workspace = create_run_workspace(root, "nested-skill-action")

            action = parse_tool_action("skill", {"name": "apps/web:testing"})
            loaded = execute_action(workspace, action)

        self.assertIsInstance(action, SkillAction)
        self.assertTrue(loaded.ok)
        self.assertEqual(loaded.name, "apps/web:testing")
        self.assertIn("Run web integration tests.", loaded.content)

    def test_project_overview_includes_skill_metadata_without_body(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-skills-") as base:
            root = Path(base)
            _write_skill(root, ".claude/skills", "review", "Review changes", "PRIVATE_REVIEW_BODY")
            workspace = create_run_workspace(root, "run-1")

            overview = execute_action(workspace, ProjectOverviewAction(type="project_overview"))

        self.assertTrue(overview.ok)
        self.assertEqual(overview.skills_total, 1)
        self.assertEqual(overview.skills[0].name, "review")
        self.assertFalse(hasattr(overview.skills[0], "content"))

    def test_skill_tools_are_loaded_on_demand_and_read_only(self) -> None:
        active = initial_agent_tool_names()

        self.assertNotIn("project_skills", active)
        self.assertNotIn("skill", active)
        self.assertNotIn("Skill", active)


if __name__ == "__main__":
    unittest.main()
