import tempfile
import unittest
from pathlib import Path

from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.agent_tool_registry import initial_agent_tool_names
from vibeagent.prompts import build_messages
from vibeagent.types import ProjectOverviewAction, ProjectSkillsAction, SkillAction
from vibeagent.workspace import create_run_workspace, format_project_skill_catalog, read_project_skill, read_project_skills


def _write_skill(root: Path, base: str, name: str, description: str, body: str) -> Path:
    path = root / base / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n", encoding="utf-8")
    return path


class ProjectSkillWorkspaceTests(unittest.TestCase):
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


class ProjectSkillActionTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
