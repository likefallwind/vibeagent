from __future__ import annotations

import json
from pathlib import Path
import sys


FAKE_LSP_SERVER = r'''from __future__ import annotations
import json
import os
from pathlib import Path
import sys

root_uri = ""
documents = {}
crash_marker = os.environ.get("FAKE_LSP_CRASH_ONCE")

def read_message():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in {b"\r\n", b"\n"}:
            break
        name, value = line.decode("ascii").split(":", 1)
        headers[name.lower()] = value.strip()
    return json.loads(sys.stdin.buffer.read(int(headers["content-length"])).decode("utf-8"))

def send(message):
    payload = json.dumps(message, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii") + payload)
    sys.stdout.buffer.flush()

def publish(uri, text):
    diagnostics = []
    if "BROKEN" in text:
        diagnostics.append({
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 6}},
            "severity": 1,
            "source": "fake-lsp",
            "message": "BROKEN token",
        })
    send({"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics", "params": {"uri": uri, "diagnostics": diagnostics}})

while True:
    message = read_message()
    if message is None:
        break
    method = message.get("method")
    params = message.get("params") or {}
    request_id = message.get("id")
    if method == "initialize":
        root_uri = params.get("rootUri", "")
        send({"jsonrpc": "2.0", "id": request_id, "result": {"capabilities": {"textDocumentSync": 1}}})
    elif method == "shutdown":
        send({"jsonrpc": "2.0", "id": request_id, "result": None})
    elif method == "exit":
        break
    elif method in {"textDocument/didOpen", "textDocument/didChange"}:
        document = params["textDocument"]
        uri = document["uri"]
        text = document.get("text", (params.get("contentChanges") or [{}])[0].get("text", ""))
        documents[uri] = text
        publish(uri, text)
    elif request_id is not None:
        if crash_marker and not Path(crash_marker).exists():
            Path(crash_marker).write_text("crashed", encoding="utf-8")
            raise SystemExit(2)
        uri = (params.get("textDocument") or {}).get("uri", root_uri + "/app.py")
        location = {"uri": uri, "range": {"start": {"line": 0, "character": 4}, "end": {"line": 0, "character": 10}}}
        if method in {"textDocument/definition", "textDocument/implementation"}:
            result = location
        elif method == "textDocument/references":
            result = [location, location]
        elif method == "textDocument/hover":
            result = {"contents": {"kind": "markdown", "value": "`greet(name)`"}}
        elif method == "textDocument/documentSymbol":
            result = [{"name": "greet", "kind": 12, "range": location["range"], "selectionRange": location["range"]}]
        elif method == "workspace/symbol":
            result = [{"name": "greet", "kind": 12, "location": location}]
        else:
            result = None
        send({"jsonrpc": "2.0", "id": request_id, "result": result})
'''


def write_lsp_plugin(root: Path, *, inline: bool = False, transport: str = "stdio") -> Path:
    plugin = root / "extensions" / "python-lsp"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / "bin").mkdir()
    (plugin / "bin" / "server.py").write_text(FAKE_LSP_SERVER, encoding="utf-8")
    server = {
        "command": sys.executable,
        "args": ["${CLAUDE_PLUGIN_ROOT}/bin/server.py"],
        "transport": transport,
        "extensionToLanguage": {".py": "python"},
        "startupTimeout": 3_000,
        "shutdownTimeout": 1_000,
    }
    manifest: dict[str, object] = {
        "name": "python-lsp",
        "description": "Test Python language server",
        "version": "1.0.0",
    }
    if inline:
        manifest["lspServers"] = {"python": server}
    else:
        (plugin / ".lsp.json").write_text(json.dumps({"python": server}), encoding="utf-8")
    (plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    return plugin


__all__ = ["write_lsp_plugin"]
