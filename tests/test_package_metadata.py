from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DESCRIPTION = (
    "Project-aware command-line coding agent with safe tools, sessions, "
    "and provider-neutral model adapters."
)


class PackageMetadataTests(unittest.TestCase):
    def test_python_and_npm_descriptions_match_v1_positioning(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

        self.assertEqual(pyproject["project"]["description"], EXPECTED_DESCRIPTION)
        self.assertEqual(package["description"], EXPECTED_DESCRIPTION)
        self.assertNotIn("MiniMax", pyproject["project"]["description"])
        self.assertNotIn("MiniMax", package["description"])


if __name__ == "__main__":
    unittest.main()
