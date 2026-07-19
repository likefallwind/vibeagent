import unittest

from vibeagent.prompts import SYSTEM_PROMPT


class PromptSystemGuidanceTests(unittest.TestCase):
    def test_system_prompt_distinguishes_file_discovery_tools(self) -> None:
        self.assertIn("find_files to find files by path or filename fragment", SYSTEM_PROMPT)
        self.assertIn("glob to find files by path pattern", SYSTEM_PROMPT)
        self.assertIn("search to find text inside files", SYSTEM_PROMPT)
        self.assertIn("search_contexts when you need matching lines plus surrounding source context", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
