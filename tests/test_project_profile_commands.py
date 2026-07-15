from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.project_profile_commands import get_agents_text, get_skills_text


class ProjectProfileCommandTests(unittest.TestCase):
    def test_agents_and_skills_text_list_metadata_without_bodies(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-profile-commands-") as base:
            root = Path(base)
            agent_dir = root / ".claude" / "agents"
            agent_dir.mkdir(parents=True)
            (agent_dir / "reviewer.md").write_text(
                "---\n"
                "name: reviewer\n"
                "description: Reviews code changes\n"
                "mode: explore\n"
                "tools: Read\n"
                "---\n\n"
                "PRIVATE_AGENT_PROMPT\n",
                encoding="utf-8",
            )
            skill_dir = root / ".agents" / "skills" / "testing"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: testing\n"
                "description: Run focused tests\n"
                "---\n\n"
                "PRIVATE_SKILL_BODY\n",
                encoding="utf-8",
            )

            agents = get_agents_text(root)
            skills = get_skills_text(root)

        self.assertIn("reviewer: Reviews code changes", agents)
        self.assertIn("tools=Read,read_file", agents)
        self.assertNotIn("PRIVATE_AGENT_PROMPT", agents)
        self.assertIn("testing: Run focused tests", skills)
        self.assertNotIn("PRIVATE_SKILL_BODY", skills)

    def test_agents_and_skills_text_report_empty_catalogs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-profile-commands-") as base:
            root = Path(base)

            agents = get_agents_text(root)
            skills = get_skills_text(root)

        self.assertEqual(agents, "No project agent profiles found.")
        self.assertEqual(skills, "No project skills found.")


if __name__ == "__main__":
    unittest.main()
