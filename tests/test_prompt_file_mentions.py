from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_runtime_utils import compact_agent_message_history
from vibeagent.prompt_file_mentions import (
    MAX_PROMPT_FILE_MENTIONS,
    PROMPT_FILE_REFERENCE_MARKER,
    find_prompt_file_mentions,
    load_prompt_file_context,
    prompt_file_context_metadata,
    prompt_file_reference_blocks,
)
from vibeagent.prompts import build_messages
from vibeagent.types import ChatMessage
from vibeagent.workspace import create_run_workspace


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class PromptFileMentionTests(unittest.TestCase):
    def test_finds_existing_and_explicit_paths_without_matching_email_or_packages(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mentions-") as base:
            root = Path(base)
            (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "with space.md").write_text("notes\n", encoding="utf-8")
            (root / 'quote"name.py').write_text("QUOTED = True\n", encoding="utf-8")
            workspace = create_run_workspace(root, "run-1")
            mentions = find_prompt_file_mentions(
                'Review @app.py, @"docs/with space.md" and @app.py; ignore a@b.com @types/node '
                "@staticmethod.",
                workspace,
            )
            context = load_prompt_file_context('@\'quote"name.py\'', workspace)
            block_text = str(prompt_file_reference_blocks(context)[0]["text"])

        self.assertEqual(mentions, ("app.py", "docs/with space.md"))
        self.assertIn('path="quote&quot;name.py"', block_text)

    def test_loads_bounded_text_and_builds_metadata_without_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mentions-") as base:
            root = Path(base)
            content = "x" * 25_000
            (root / "large.py").write_text(content, encoding="utf-8")
            context = load_prompt_file_context("Inspect @large.py", create_run_workspace(root, "run-1"))
            blocks = prompt_file_reference_blocks(context)
            metadata = prompt_file_context_metadata(context)

        self.assertEqual(context.count, 1)
        self.assertTrue(context.text_files[0].truncated)
        self.assertEqual(context.text_files[0].total_bytes, 25_000)
        self.assertLess(len(context.text_files[0].content.encode("utf-8")), 21_000)
        self.assertTrue(str(blocks[0]["text"]).startswith(PROMPT_FILE_REFERENCE_MARKER))
        self.assertIn("[file truncated]", str(blocks[0]["text"]))
        self.assertEqual(metadata["files"][0]["bytes"], 25_000)
        self.assertNotIn("content", metadata["files"][0])

    def test_loads_image_as_provider_neutral_one_turn_block(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mentions-") as base:
            root = Path(base)
            (root / "pixel.png").write_bytes(PNG_1X1)
            context = load_prompt_file_context("Inspect @pixel.png", create_run_workspace(root, "run-1"))
            blocks = prompt_file_reference_blocks(context)
            metadata = prompt_file_context_metadata(context)

        self.assertEqual(len(context.images), 1)
        self.assertEqual((context.images[0].width, context.images[0].height), (1, 1))
        self.assertEqual(blocks[1]["type"], "image")
        self.assertEqual(blocks[1]["source"]["media_type"], "image/png")
        self.assertEqual(base64.b64decode(blocks[1]["source"]["data"]), PNG_1X1)
        self.assertNotIn("data", metadata["files"][0])

    def test_rejects_missing_escaping_sensitive_binary_and_excess_mentions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mentions-") as base:
            root = Path(base)
            (root / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
            (root / "binary.bin").write_bytes(b"\x00\x01")
            for index in range(MAX_PROMPT_FILE_MENTIONS + 1):
                (root / f"file{index}.py").write_text("x\n", encoding="utf-8")
            workspace = create_run_workspace(root, "run-1")

            failures = {
                "missing": "Inspect @missing.py",
                "escape": "Inspect @../outside.py",
                "sensitive": "Inspect @.env",
                "binary": "Inspect @binary.bin",
                "excess": "Inspect " + " ".join(
                    f"@file{index}.py" for index in range(MAX_PROMPT_FILE_MENTIONS + 1)
                ),
            }
            for label, task in failures.items():
                with self.subTest(label=label), self.assertRaises(ValueError):
                    load_prompt_file_context(task, workspace)

    def test_compaction_retains_prompt_file_reference_blocks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mentions-") as base:
            root = Path(base)
            (root / "app.py").write_text("REFERENCE_VALUE = 7\n", encoding="utf-8")
            workspace = create_run_workspace(root, "run-1")
            context = load_prompt_file_context("Review @app.py", workspace)
            messages = build_messages("Review @app.py", workspace, prompt_file_context=context)
            messages.extend(
                [
                    ChatMessage(role="assistant", content="old response " + "x" * 2_000),
                    ChatMessage(role="user", content="old follow-up " + "y" * 2_000),
                ]
            )
            compacted = compact_agent_message_history(
                "Review @app.py",
                workspace,
                messages,
                [],
                [],
                None,
                2,
                threshold=1,
            )

        prompt = str(compacted[1].content)
        self.assertLess(len(compacted), len(messages))
        self.assertIn(PROMPT_FILE_REFERENCE_MARKER, prompt)
        self.assertIn("REFERENCE_VALUE = 7", prompt)


if __name__ == "__main__":
    unittest.main()
