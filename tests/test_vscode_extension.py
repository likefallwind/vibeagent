from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
EXTENSION_ROOT = ROOT / "extensions" / "vscode"


class VsCodeExtensionTests(unittest.TestCase):
    def test_manifest_exposes_the_bounded_ide_commands(self) -> None:
        manifest = json.loads((EXTENSION_ROOT / "package.json").read_text(encoding="utf-8"))
        commands = {item["command"] for item in manifest["contributes"]["commands"]}
        self.assertEqual(
            commands,
            {
                "vibeagent.open",
                "vibeagent.askSelection",
                "vibeagent.insertReference",
                "vibeagent.sendDiagnostics",
                "vibeagent.reviewCurrentFile",
            },
        )
        self.assertEqual(manifest["main"], "./extension.js")
        self.assertEqual(manifest["engines"]["vscode"], "^1.98.0")
        properties = manifest["contributes"]["configuration"]["properties"]
        self.assertEqual(properties["vibeagent.executable"]["scope"], "machine")
        self.assertEqual(properties["vibeagent.arguments"]["scope"], "machine")

    def test_javascript_sources_parse_and_core_contract_passes(self) -> None:
        for relative in ("extension.js", "src/core.js"):
            result = subprocess.run(
                ["node", "--check", relative],
                cwd=EXTENSION_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(
            ["node", "--test", "test/core.test.js", "test/extension.test.js"],
            cwd=EXTENSION_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_vsix_build_is_deterministic_and_contains_only_declared_sources(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-vsix-") as base:
            first = Path(base) / "first.vsix"
            second = Path(base) / "second.vsix"
            for output in (first, second):
                result = subprocess.run(
                    [sys.executable, "scripts/build_vscode_extension.py", "--output", str(output)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {
                        "[Content_Types].xml",
                        "extension.vsixmanifest",
                        "extension/package.json",
                        "extension/extension.js",
                        "extension/README.md",
                        "extension/src/core.js",
                    },
                )
                manifest = archive.read("extension.vsixmanifest").decode("utf-8")
                self.assertIn('Id="vibeagent-vscode"', manifest)
                self.assertIn('Version="1.0.0"', manifest)


if __name__ == "__main__":
    unittest.main()
