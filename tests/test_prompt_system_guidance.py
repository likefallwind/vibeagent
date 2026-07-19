import unittest

from vibeagent.prompts import SYSTEM_PROMPT


class PromptSystemGuidanceTests(unittest.TestCase):
    def test_system_prompt_guides_project_skill_discovery(self) -> None:
        self.assertIn("Use project_skills to list project skill metadata", SYSTEM_PROMPT)
        self.assertIn("need the exact skill name before loading one", SYSTEM_PROMPT)
        self.assertIn("load only the needed skill by exact name", SYSTEM_PROMPT)

    def test_system_prompt_guides_project_agent_profile_discovery(self) -> None:
        self.assertIn("Use project_agents to list project subagent profile metadata", SYSTEM_PROMPT)
        self.assertIn("need the exact profile name before delegating", SYSTEM_PROMPT)
        self.assertIn("pass its exact name in agent", SYSTEM_PROMPT)

    def test_system_prompt_distinguishes_file_discovery_tools(self) -> None:
        self.assertIn("find_files to find files by path or filename fragment", SYSTEM_PROMPT)
        self.assertIn("glob to find files by path pattern", SYSTEM_PROMPT)
        self.assertIn("search to find text inside files", SYSTEM_PROMPT)
        self.assertIn("search_contexts when you need matching lines plus surrounding source context", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
