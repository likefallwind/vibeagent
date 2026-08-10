from __future__ import annotations

import hashlib
import os
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Condition, Lock, Thread, current_thread
import time
from typing import BinaryIO

from .lsp_config import LspServerConfig
from .lsp_protocol import encode_lsp_message, read_lsp_message
from .lsp_process import LspProcess
from .workspace_file_helpers import read_utf8_text_file
from .workspace_resolve import resolve_inside_run


LSP_MAX_SOURCE_BYTES = 2_000_000


class LspClient:
    def __init__(self, project_root: Path, config: LspServerConfig) -> None:
        self.project_root = project_root.resolve()
        self.config = config
        self._transport = LspProcess(config)
        self._state_lock = Lock()
        self._document_lock = Lock()
        self._diagnostic_condition = Condition(self._state_lock)
        self._pending: dict[int, Queue[object]] = {}
        self._documents: dict[str, tuple[str, int]] = {}
        self._diagnostics: dict[str, list[object]] = {}
        self._diagnostic_revisions: dict[str, int] = {}
        self._next_id = 1
        self._reader_error: BaseException | None = None
        self._reader_thread: Thread | None = None

    @property
    def running(self) -> bool:
        return self._transport.running and self._reader_error is None

    def start(self) -> None:
        if self.running:
            return
        self.close()
        self._reader_error = None
        self._reader_thread = Thread(
            target=self._read_loop,
            args=(self._transport.start(),),
            daemon=True,
        )
        self._reader_thread.start()
        try:
            self.request(
                "initialize",
                {
                    "processId": os.getpid(),
                    "rootUri": self.config.workspace_folder.as_uri(),
                    "capabilities": {"textDocument": {"publishDiagnostics": {}}},
                    "initializationOptions": self.config.initialization_options,
                    "workspaceFolders": [
                        {"uri": self.config.workspace_folder.as_uri(), "name": self.config.workspace_folder.name}
                    ],
                },
                timeout_ms=self.config.startup_timeout_ms,
            )
            self.notify("initialized", {})
            if self.config.settings:
                self.notify("workspace/didChangeConfiguration", {"settings": self.config.settings})
        except Exception:
            self.close()
            raise

    def request(self, method: str, params: object, *, timeout_ms: int | None = None) -> object:
        self._require_running()
        with self._state_lock:
            request_id = self._next_id
            self._next_id += 1
            response: Queue[object] = Queue(maxsize=1)
            self._pending[request_id] = response
        try:
            self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
            try:
                selected = response.get(timeout=(timeout_ms or self.config.startup_timeout_ms) / 1000)
            except Empty as error:
                raise TimeoutError(f"LSP server {self.config.name} timed out during {method}.") from error
            if isinstance(selected, BaseException):
                raise ValueError(f"LSP server {self.config.name} failed: {selected}") from selected
            assert isinstance(selected, dict)
            if "error" in selected:
                raise ValueError(f"LSP server {self.config.name} returned an error for {method}: {selected['error']}")
            return selected.get("result")
        finally:
            with self._state_lock:
                self._pending.pop(request_id, None)

    def notify(self, method: str, params: object) -> None:
        self._require_running()
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def ensure_document(self, relative_path: str) -> tuple[Path, str, int]:
        with self._document_lock:
            return self._ensure_document_locked(relative_path)

    def _ensure_document_locked(self, relative_path: str) -> tuple[Path, str, int]:
        target = resolve_inside_run(self.project_root, relative_path)
        if not target.is_file() or target.stat().st_size > LSP_MAX_SOURCE_BYTES:
            raise ValueError(f"LSP source file is missing or exceeds {LSP_MAX_SOURCE_BYTES} bytes: {relative_path}")
        text = read_utf8_text_file(target, relative_path)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        uri = target.as_uri()
        with self._state_lock:
            previous = self._documents.get(uri)
            revision = self._diagnostic_revisions.get(uri, 0)
        language = next(
            value
            for extension, value in self.config.extension_to_language.items()
            if extension.lower() == target.suffix.lower()
        )
        if previous is None:
            version = 1
            self.notify(
                "textDocument/didOpen",
                {"textDocument": {"uri": uri, "languageId": language, "version": version, "text": text}},
            )
        elif previous[0] != digest:
            version = previous[1] + 1
            self.notify(
                "textDocument/didChange",
                {"textDocument": {"uri": uri, "version": version}, "contentChanges": [{"text": text}]},
            )
        else:
            return target, uri, revision
        with self._state_lock:
            self._documents[uri] = (digest, version)
        return target, uri, revision

    def wait_for_diagnostics(self, uri: str, revision: int, timeout_ms: int = 500) -> list[object]:
        deadline = time.monotonic() + timeout_ms / 1000
        with self._diagnostic_condition:
            while self._diagnostic_revisions.get(uri, 0) <= revision and self.running:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._diagnostic_condition.wait(remaining)
            if self._diagnostic_revisions.get(uri, 0) <= revision:
                return []
            return list(self._diagnostics.get(uri, []))

    def close(self) -> None:
        if self._transport.process is None:
            return
        if self._transport.running:
            try:
                self.request("shutdown", None, timeout_ms=self.config.shutdown_timeout_ms)
                self.notify("exit", None)
            except Exception:
                pass
        self._transport.stop()
        reader = self._reader_thread
        if reader is not None and reader is not current_thread():
            reader.join(timeout=1)
        self._reader_thread = None
        with self._state_lock:
            error = EOFError("LSP client closed.")
            for pending in self._pending.values():
                try:
                    pending.put_nowait(error)
                except Full:
                    pass
            self._pending.clear()
            self._documents.clear()

    def stderr_summary(self) -> str:
        return self._transport.stderr_summary()

    def _write(self, message: dict[str, object]) -> None:
        payload = encode_lsp_message(message)
        self._transport.write(payload)

    def _require_running(self) -> None:
        if not self.running:
            stderr = self.stderr_summary()
            detail = f" stderr={stderr}" if stderr else ""
            raise ValueError(f"LSP server {self.config.name} is not running.{detail}")

    def _read_loop(self, stream: BinaryIO) -> None:
        try:
            while True:
                message = read_lsp_message(stream)
                self._dispatch(message)
        except BaseException as error:
            with self._diagnostic_condition:
                self._reader_error = error
                for pending in self._pending.values():
                    try:
                        pending.put_nowait(error)
                    except Full:
                        pass
                self._diagnostic_condition.notify_all()

    def _dispatch(self, message: dict[str, object]) -> None:
        request_id = message.get("id")
        if isinstance(request_id, int):
            if isinstance(message.get("method"), str):
                self._answer_server_request(request_id, str(message["method"]), message.get("params"))
                return
            with self._state_lock:
                pending = self._pending.get(request_id)
            if pending is not None:
                try:
                    pending.put_nowait(message)
                except Full:
                    pass
            return
        if message.get("method") != "textDocument/publishDiagnostics":
            return
        params = message.get("params")
        if not isinstance(params, dict) or not isinstance(params.get("uri"), str):
            return
        diagnostics = params.get("diagnostics", [])
        if not isinstance(diagnostics, list):
            return
        uri = params["uri"]
        with self._diagnostic_condition:
            self._diagnostics[uri] = diagnostics[:1_000]
            self._diagnostic_revisions[uri] = self._diagnostic_revisions.get(uri, 0) + 1
            self._diagnostic_condition.notify_all()

    def _answer_server_request(self, request_id: int, method: str, params: object) -> None:
        if method == "workspace/configuration":
            items = params.get("items", []) if isinstance(params, dict) else []
            result: object = [self.config.settings for _item in items] if isinstance(items, list) else []
            self._write({"jsonrpc": "2.0", "id": request_id, "result": result})
            return
        if method in {"client/registerCapability", "client/unregisterCapability", "window/workDoneProgress/create"}:
            self._write({"jsonrpc": "2.0", "id": request_id, "result": None})
            return
        self._write(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unsupported server request: {method}"},
            }
        )

__all__ = ["LspClient"]
