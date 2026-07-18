from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

from vibeagent import __version__


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

    def test_version_metadata_matches_runtime_and_npm_lockfile(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        package_lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))

        self.assertEqual(__version__, "1.0.0")
        self.assertEqual(pyproject["project"]["version"], __version__)
        self.assertEqual(package["version"], __version__)
        self.assertEqual(package_lock["version"], __version__)
        self.assertEqual(package_lock["packages"][""]["version"], __version__)


if __name__ == "__main__":
    unittest.main()
