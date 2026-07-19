import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliFileImageInfoFlagTests(unittest.TestCase):
    def test_main_runs_file_info_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_file_info_text", return_value="File info:\n  paths: 1/1") as get_file_info_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--file-info", "src/app.py", "asset.bin"])

        self.assertEqual(exit_code, 0)
        self.assertIn("File info:", stdout.getvalue())
        get_file_info_text.assert_called_once_with(Path(base).resolve(), ["src/app.py", "asset.bin"])
        create_chat_client.assert_not_called()

    def test_main_runs_image_info_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_image_info_text", return_value="Image info:\n  images: 1/1") as get_image_info_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--image-info", "assets/logo.png"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Image info:", stdout.getvalue())
        get_image_info_text.assert_called_once_with(Path(base).resolve(), ["assets/logo.png"])
        create_chat_client.assert_not_called()

    def test_main_file_and_image_info_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "assets").mkdir()
            (root / "src" / "app.py").write_text("one\ntwo\n", encoding="utf-8")
            (root / "asset.bin").write_bytes(b"\x00\x01")
            (root / "assets" / "logo.png").write_bytes(
                b"\x89PNG\r\n\x1a\n"
                b"\x00\x00\x00\rIHDR"
                + (13).to_bytes(4, "big")
                + (17).to_bytes(4, "big")
                + b"\x08\x02\x00\x00\x00\x00\x00\x00\x00"
            )

            def run_json(*argv: str) -> tuple[int, dict[str, object]]:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(["--json", "--cwd", base, *argv])
                return exit_code, json.loads(stdout.getvalue())

            with patch("vibeagent.cli.create_chat_client") as create_chat_client:
                file_exit, file_payload = run_json("--file-info", "src/app.py", "src", "asset.bin")
                image_exit, image_payload = run_json("--image-info", "assets/logo.png", "assets")

        self.assertEqual(file_exit, 0)
        self.assertEqual(file_payload["fileInfo"]["paths"]["ok"], 3)
        self.assertEqual(file_payload["fileInfo"]["paths"]["items"][0]["path"], "src/app.py")
        self.assertEqual(file_payload["fileInfo"]["paths"]["items"][0]["type"], "file")
        self.assertEqual(file_payload["fileInfo"]["paths"]["items"][0]["lineCount"], 2)
        self.assertEqual(file_payload["fileInfo"]["paths"]["items"][1]["type"], "directory")
        self.assertTrue(file_payload["fileInfo"]["paths"]["items"][2]["binary"])
        self.assertEqual(image_exit, 1)
        self.assertEqual(image_payload["status"], "failed")
        self.assertEqual(image_payload["imageInfo"]["images"]["ok"], 1)
        self.assertEqual(image_payload["imageInfo"]["images"]["total"], 2)
        self.assertEqual(image_payload["imageInfo"]["images"]["items"][0]["format"], "png")
        self.assertEqual(image_payload["imageInfo"]["images"]["items"][0]["width"], 13)
        self.assertIn("Path is not a file", image_payload["imageInfo"]["images"]["items"][1]["message"])
        create_chat_client.assert_not_called()
