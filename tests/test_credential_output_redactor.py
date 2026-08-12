from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from vibeagent.credential_output_redactor import (
    MASKED_CREDENTIAL,
    StreamingCredentialRedactor,
)


class StreamingCredentialRedactorTests(unittest.TestCase):
    def test_masks_secrets_across_chunks_and_prefers_longest_match(self) -> None:
        redactor = StreamingCredentialRedactor([b"token", b"token-long"])

        output = b"".join(
            (
                redactor.feed(b"before to"),
                redactor.feed(b"ken-lo"),
                redactor.feed(b"ng after"),
                redactor.feed(b"", final=True),
            )
        )

        self.assertEqual(output, b"before " + MASKED_CREDENTIAL + b" after")

    def test_masks_overlapping_repetitions_without_retaining_secret_bytes(self) -> None:
        redactor = StreamingCredentialRedactor([b"aba"])

        output = redactor.feed(b"ababa", final=True)

        self.assertEqual(output, MASKED_CREDENTIAL + b"ba")
        self.assertNotIn(b"aba", output)

    def test_empty_secret_set_passes_bytes_through(self) -> None:
        redactor = StreamingCredentialRedactor([])

        self.assertEqual(redactor.feed(b"plain", final=True), b"plain")


class CredentialLauncherTests(unittest.TestCase):
    def test_launcher_masks_environment_and_file_values_on_both_streams(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-credential-mask-") as base:
            root = Path(base)
            secret_file = root / "credential.txt"
            secret_file.write_bytes(b"file-secret\n")
            config = json.dumps(
                {
                    "env": ["VIBEAGENT_MASK_TEST"],
                    "files": [secret_file.as_posix()],
                }
            )
            environment = dict(os.environ)
            environment["VIBEAGENT_MASK_TEST"] = "environment-secret"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "vibeagent.sandbox_credential_launcher",
                    "--config-json",
                    config,
                    "--",
                    sys.executable,
                    "-c",
                    (
                        "import os,sys; "
                        "sys.stdout.write(os.environ['VIBEAGENT_MASK_TEST']); "
                        "sys.stderr.write(open(sys.argv[1]).read())"
                    ),
                    secret_file.as_posix(),
                ],
                cwd=root,
                env=environment,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, MASKED_CREDENTIAL)
        self.assertEqual(result.stderr, MASKED_CREDENTIAL)
        self.assertNotIn(b"environment-secret", result.stdout)
        self.assertNotIn(b"file-secret", result.stderr)

    def test_launcher_fails_closed_for_missing_mask_file(self) -> None:
        config = json.dumps({"env": [], "files": ["/missing/credential"]})

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "vibeagent.sandbox_credential_launcher",
                "--config-json",
                config,
                "--",
                sys.executable,
                "-c",
                "print('must-not-run')",
            ],
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 126)
        self.assertNotIn(b"must-not-run", result.stdout)
        self.assertIn(b"Credential masking failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
