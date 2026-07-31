from __future__ import annotations

import hashlib
import unittest

import vibeagent.agent_approval_preview_keys as preview_keys
import vibeagent.types as types_module
from vibeagent.types import CheckFocusedTestCommandsObservation


class ApprovalPreviewKeyTests(unittest.TestCase):
    def test_git_stash_preview_key_uses_default_message(self) -> None:
        action_key = preview_keys.approval_preview_key(types_module.GitStashAction(type="git_stash"))
        observation_key = preview_keys.approval_preview_key(
            types_module.CheckGitStashObservation(
                kind="check_git_stash",
                ok=True,
                message_text="vibeagent stash",
                include_untracked=False,
                status=" M app.py\n",
                diff="",
                message="Can stash 1 path(s).",
            )
        )

        self.assertEqual(action_key, observation_key)

    def test_focused_test_preview_paths_distinguish_explicit_from_auto_paths(self) -> None:
        preview_observation = CheckFocusedTestCommandsObservation(
            kind="check_focused_test_commands",
            ok=True,
            checks=[],
            focused_commands=[],
            target_paths=["vibeagent/agent.py"],
            total=0,
            truncated=False,
            max_commands=3,
            related_tests_total=0,
            message="Preflighted 0/0 focused test command(s); 0 failed.",
            max_paths=5,
            max_candidates=20,
            requested_paths=[],
        )

        auto_key = preview_keys.approval_preview_key(
            types_module.RunFocusedTestCommandsAction(
                type="run_focused_test_commands",
                max_paths=5,
                max_candidates=20,
                max_commands=3,
            )
        )
        explicit_key = preview_keys.approval_preview_key(
            types_module.RunFocusedTestCommandsAction(
                type="run_focused_test_commands",
                paths=["vibeagent/agent.py"],
                max_paths=5,
                max_candidates=20,
                max_commands=3,
            )
        )
        observation_key = preview_keys.approval_preview_key(preview_observation)

        self.assertEqual(auto_key, observation_key)
        self.assertNotEqual(explicit_key, observation_key)

    def test_write_process_preview_key_hashes_action_content(self) -> None:
        content = "hello\n"
        expected_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()

        action_key = preview_keys.approval_preview_key(
            types_module.WriteProcessAction(type="write_process", process_id="proc-1", content=content)
        )
        observation_key = preview_keys.approval_preview_key(
            types_module.CheckWriteProcessObservation(
                kind="check_write_process",
                process_id="proc-1",
                pid=123,
                ok=True,
                running=True,
                command="python server.py",
                cwd=".",
                content_chars=len(content),
                message="Can write process input.",
                content_sha256=expected_digest,
            )
        )

        self.assertEqual(action_key, ("write_process", "proc-1", expected_digest))
        self.assertEqual(action_key, observation_key)


if __name__ == "__main__":
    unittest.main()
