import http.client
import json
import tempfile
import threading
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch

from vibeagent.background_agent_types import BackgroundAgentRecord, BackgroundAgentView
from vibeagent.background_agent_approval import BackgroundApproval
from vibeagent.background_agent_changes import BackgroundAgentChangedFile, BackgroundAgentChanges
from vibeagent.background_agent_input import BackgroundUserInput
from vibeagent.background_agent_integration import BackgroundAgentIntegration
from vibeagent.cli import main
from vibeagent.cli_args import parse_args
from vibeagent.cli_validation import validate_cli_args
from vibeagent.remote_control_server import create_remote_control_server
from vibeagent.remote_control_assets import REMOTE_CONTROL_JS
from vibeagent.types import UserInputRequest


AGENT_ID = "0123456789ab"


class FakeBackend:
    def __init__(self, root: Path) -> None:
        record = BackgroundAgentRecord(
            id=AGENT_ID,
            project_root=root,
            invocation_root=root,
            pid=123,
            start_ticks=1,
            started_at="2026-08-11T00:00:00+00:00",
            task_summary="fix tests",
            session_name="test-session",
            stdout_path=root / "stdout.log",
            stderr_path=root / "stderr.log",
            exit_code_path=root / "exit",
            stopped_path=root / "stopped",
        )
        self.views = [BackgroundAgentView(record=record, status="running", exit_code=None)]
        self.calls: list[tuple[object, ...]] = []
        self.approval_value = None
        self.question_value = None

    def list(self):
        return tuple(self.views)

    def pending(self, agent_id):
        return 2

    def logs(self, agent_id):
        self.calls.append(("logs", agent_id))
        return "stdout\n", "stderr\n"

    def changes(self, agent_id):
        self.calls.append(("changes", agent_id))
        return BackgroundAgentChanges(
            agent_id=agent_id,
            session_root=self.views[0].record.project_root / ".vibeagent/worktrees/review",
            isolated=True,
            branch="vibeagent/review",
            base_commit="a" * 40,
            head_commit="b" * 40,
            snapshot_id="c" * 64,
            files=(
                BackgroundAgentChangedFile(
                    path="src/app.py",
                    committed=True,
                    staged=False,
                    unstaged=False,
                    untracked=False,
                    deleted=False,
                    fingerprint=f"file:-:{'d' * 40}",
                ),
            ),
            omitted_files=0,
        )

    def change_content(self, agent_id, path, side):
        self.calls.append(("change-content", agent_id, path, side))
        return "old\n" if side == "base" else "new\n"

    def integrate(self, agent_id, snapshot_id):
        self.calls.append(("integrate", agent_id, snapshot_id))
        return BackgroundAgentIntegration(
            agent_id=agent_id,
            snapshot_id=snapshot_id,
            applied_files=("src/app.py",),
            skipped_files=("README.md",),
        )

    def approval(self, agent_id):
        return self.approval_value

    def user_input(self, agent_id):
        return self.question_value

    def answer_user_input(self, agent_id, answer, request_id=None):
        self.calls.append(("answer", agent_id, answer, request_id))
        return "answered"

    def decide_approval(self, agent_id, approved, scope, request_id=None):
        self.calls.append(("approval", agent_id, approved, scope, request_id))
        return "decided"

    def dispatch(self, task):
        self.calls.append(("dispatch", task))
        return self.views[0]

    def reply(self, agent_id, message):
        self.calls.append(("reply", agent_id, message))
        return "queued"

    def stop(self, agent_id):
        self.calls.append(("stop", agent_id))
        return "stopped"

    def respawn(self, agent_id):
        self.calls.append(("respawn", agent_id))
        return "respawned"

    def remove(self, agent_id):
        self.calls.append(("remove", agent_id))
        return "removed"


class RemoteControlServerTests(unittest.TestCase):
    def test_browser_javascript_is_syntax_valid(self) -> None:
        result = subprocess.run(
            ["node", "--check"],
            input=REMOTE_CONTROL_JS,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="vibeagent-remote-control-")
        self.root = Path(self.temp.name).resolve()
        self.backend = FakeBackend(self.root)
        self.server = create_remote_control_server(
            self.root,
            backend=self.backend,
            token="t" * 43,
            name="devbox-a1b2c3",
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.httpd.server_address[1]

    def tearDown(self) -> None:
        self.server.httpd.shutdown()
        self.server.close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, payload=None, *, authorized=True):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        headers = {}
        body = None
        if authorized:
            headers["Authorization"] = f"Bearer {self.server.token}"
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        headers_out = dict(response.getheaders())
        connection.close()
        return response.status, headers_out, raw

    def test_assets_are_public_but_api_requires_exact_bearer_token(self) -> None:
        status, headers, body = self.request("GET", "/", authorized=False)
        self.assertEqual(status, 200)
        self.assertIn(b"VibeAgent Remote Control", body)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["Cache-Control"], "no-store")

        status, headers, body = self.request("GET", "/api/state", authorized=False)
        self.assertEqual(status, 401)
        self.assertEqual(headers["WWW-Authenticate"], "Bearer")
        self.assertIn(b"invalid", body)

    def test_state_and_logs_expose_bounded_control_data(self) -> None:
        status, _, body = self.request("GET", "/api/state")
        payload = json.loads(body)

        self.assertEqual(status, 200)
        self.assertEqual(payload["remoteControlName"], "devbox-a1b2c3")
        self.assertEqual(payload["projectRoot"], self.root.as_posix())
        self.assertEqual(payload["agents"][0]["id"], AGENT_ID)
        self.assertEqual(payload["agents"][0]["pending"], 2)
        self.assertNotIn("stdoutPath", payload["agents"][0])

        status, _, body = self.request("GET", f"/api/agents/{AGENT_ID}/logs")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"stdout": "stdout\n", "stderr": "stderr\n"})

    def test_change_routes_expose_bounded_review_data(self) -> None:
        status, _, body = self.request("GET", f"/api/agents/{AGENT_ID}/changes")
        payload = json.loads(body)

        self.assertEqual(status, 200)
        self.assertTrue(payload["isolated"])
        self.assertEqual(payload["branch"], "vibeagent/review")
        self.assertEqual(payload["files"][0]["path"], "src/app.py")
        self.assertEqual(self.backend.calls[-1], ("changes", AGENT_ID))

        status, _, body = self.request(
            "GET",
            f"/api/agents/{AGENT_ID}/change?path=src%2Fapp.py&side=base",
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["content"], "old\n")
        self.assertEqual(
            self.backend.calls[-1],
            ("change-content", AGENT_ID, "src/app.py", "base"),
        )

        for query in ("side=base", "path=src%2Fapp.py", "path=a&path=b&side=current"):
            with self.subTest(query=query):
                status, _, body = self.request(
                    "GET",
                    f"/api/agents/{AGENT_ID}/change?{query}",
                )
                self.assertEqual(status, 400)
                self.assertIn(b"query field", body)

    def test_state_serializes_approval_and_structured_question_contracts(self) -> None:
        self.backend.approval_value = BackgroundApproval(
            agent_id=AGENT_ID,
            request_id="a" * 32,
            action_type="run_command",
            target="npm test",
            risk="Runs project tests",
            preview=None,
            created_at="2026-08-11T00:00:00+00:00",
        )
        self.backend.question_value = BackgroundUserInput(
            agent_id=AGENT_ID,
            request_id="b" * 32,
            request=UserInputRequest(
                question="Choose a suite",
                options=["Focused", "Full"],
                allow_free_text=False,
                header="Tests",
                option_descriptions={"Focused": "Fast", "Full": "Complete"},
                multi_select=False,
            ),
            created_at="2026-08-11T00:00:00+00:00",
        )

        status, _, body = self.request("GET", "/api/state")
        agent = json.loads(body)["agents"][0]

        self.assertEqual(status, 200)
        self.assertEqual(agent["approval"]["actionType"], "run_command")
        self.assertEqual(agent["question"]["options"], ["Focused", "Full"])
        self.assertEqual(
            agent["question"]["optionDescriptions"],
            {"Focused": "Fast", "Full": "Complete"},
        )

    def test_mutations_route_through_agent_view_backend(self) -> None:
        cases = [
            ("/api/agents", {"task": "new task"}, ("dispatch", "new task"), 201),
            (f"/api/agents/{AGENT_ID}/messages", {"message": "continue"}, ("reply", AGENT_ID, "continue"), 200),
            (f"/api/agents/{AGENT_ID}/approval", {"approved": True, "scope": "session", "requestId": "a" * 32}, ("approval", AGENT_ID, True, "session", "a" * 32), 200),
            (f"/api/agents/{AGENT_ID}/answer", {"answer": "1", "requestId": "b" * 32}, ("answer", AGENT_ID, "1", "b" * 32), 200),
            (f"/api/agents/{AGENT_ID}/stop", {}, ("stop", AGENT_ID), 200),
            (f"/api/agents/{AGENT_ID}/respawn", {}, ("respawn", AGENT_ID), 200),
            (f"/api/agents/{AGENT_ID}/remove", {}, ("remove", AGENT_ID), 200),
        ]
        for path, payload, expected, expected_status in cases:
            with self.subTest(path=path):
                status, _, _ = self.request("POST", path, payload)
                self.assertEqual(status, expected_status)
                self.assertEqual(self.backend.calls[-1], expected)

        snapshot_id = "c" * 64
        status, _, body = self.request(
            "POST",
            f"/api/agents/{AGENT_ID}/integrate",
            {"snapshotId": snapshot_id},
        )
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(self.backend.calls[-1], ("integrate", AGENT_ID, snapshot_id))
        self.assertEqual(payload["appliedFiles"], ["src/app.py"])
        self.assertEqual(payload["skippedFiles"], ["README.md"])

    def test_rejects_invalid_routes_payloads_and_non_tls_network_bind(self) -> None:
        status, _, _ = self.request(
            "POST",
            f"/api/agents/{AGENT_ID}/approval",
            {"approved": "yes"},
        )
        self.assertEqual(status, 400)

        for payload in (
            {"approved": True},
            {"approved": True, "requestId": "A" * 32},
        ):
            with self.subTest(payload=payload):
                status, _, body = self.request(
                    "POST",
                    f"/api/agents/{AGENT_ID}/approval",
                    payload,
                )
                self.assertEqual(status, 400)
                self.assertIn(b"requestId", body)

        status, _, body = self.request(
            "POST",
            f"/api/agents/{AGENT_ID}/answer",
            {"answer": "1"},
        )
        self.assertEqual(status, 400)
        self.assertIn(b"requestId", body)

        for payload in ({}, {"snapshotId": "C" * 64}, {"snapshotId": "c" * 63}):
            with self.subTest(payload=payload):
                status, _, body = self.request(
                    "POST",
                    f"/api/agents/{AGENT_ID}/integrate",
                    payload,
                )
                self.assertEqual(status, 400)
                self.assertIn(b"snapshotId", body)

        status, _, _ = self.request("POST", "/api/agents/not-an-id/stop", {})
        self.assertEqual(status, 404)

        with self.assertRaisesRegex(ValueError, "requires a TLS"):
            create_remote_control_server(self.root, host="0.0.0.0")
        with self.assertRaisesRegex(ValueError, "control characters"):
            create_remote_control_server(self.root, name="bad\nname")

    def test_rejects_oversized_request_body_before_reading_it(self) -> None:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.putrequest("POST", "/api/agents")
        connection.putheader("Authorization", f"Bearer {self.server.token}")
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", str(64 * 1024 + 1))
        connection.endheaders()

        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.close()

        self.assertEqual(response.status, 400)
        self.assertIn("must not exceed", payload["error"])

    def test_cli_alias_validation_and_routing(self) -> None:
        args = parse_args(["remote-control", "--remote-control-port", "8123"])
        self.assertTrue(args.remote_control)
        self.assertEqual(args.remote_control_port, 8123)
        self.assertIsNone(validate_cli_args(args))

        self.assertIn(
            "require --remote-control",
            validate_cli_args(parse_args(["--remote-control-port", "8123"])) or "",
        )
        with patch("vibeagent.cli.run_remote_control_from_cli", return_value=0) as run:
            self.assertEqual(main(["remote-control"]), 0)
        run.assert_called_once()

    def test_cli_accepts_explicit_and_auto_remote_control_names(self) -> None:
        explicit = parse_args(["--remote-control", "release console"])
        automatic = parse_args(
            ["remote-control", "--remote-control-session-name-prefix", "devbox"]
        )

        self.assertEqual(explicit.remote_control, "release console")
        self.assertIs(explicit.remote_control_session_name_prefix, None)
        self.assertIs(automatic.remote_control, True)
        self.assertEqual(automatic.remote_control_session_name_prefix, "devbox")
        self.assertIsNone(validate_cli_args(explicit))
        self.assertIsNone(validate_cli_args(automatic))

        missing_mode = parse_args(["--remote-control-session-name-prefix", "devbox"])
        self.assertIn("require --remote-control", validate_cli_args(missing_mode) or "")

        invalid = parse_args(["--remote-control", "bad\nname"])
        self.assertIn("control characters", validate_cli_args(invalid) or "")


if __name__ == "__main__":
    unittest.main()
