from __future__ import annotations

import argparse
import os
import socket
import subprocess
import threading


PROXY_HOST = "127.0.0.1"
PROXY_PORT = 41873


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--socket", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        parser.error("a command is required")

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((PROXY_HOST, PROXY_PORT))
    listener.listen(64)
    stop = threading.Event()
    server = threading.Thread(
        target=_serve_relay,
        args=(listener, args.socket, stop),
        daemon=True,
    )
    server.start()
    environment = dict(os.environ)
    proxy_url = f"http://{PROXY_HOST}:{PROXY_PORT}"
    environment.update(
        {
            "HTTP_PROXY": proxy_url,
            "HTTPS_PROXY": proxy_url,
            "http_proxy": proxy_url,
            "https_proxy": proxy_url,
            "NO_PROXY": "",
            "no_proxy": "",
        }
    )
    environment.pop("ALL_PROXY", None)
    environment.pop("all_proxy", None)
    try:
        return subprocess.run(command, env=environment, check=False).returncode
    finally:
        stop.set()
        listener.close()
        server.join(timeout=1)


def _serve_relay(listener: socket.socket, socket_path: str, stop: threading.Event) -> None:
    listener.settimeout(0.2)
    while not stop.is_set():
        try:
            client, _address = listener.accept()
        except TimeoutError:
            continue
        except OSError:
            return
        threading.Thread(
            target=_relay_connection,
            args=(client, socket_path),
            daemon=True,
        ).start()


def _relay_connection(client: socket.socket, socket_path: str) -> None:
    with client:
        try:
            upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            upstream.connect(socket_path)
        except OSError:
            return
        with upstream:
            _relay_bidirectional(client, upstream)


def _relay_bidirectional(left: socket.socket, right: socket.socket) -> None:
    threads = (
        threading.Thread(target=_copy_socket, args=(left, right), daemon=True),
        threading.Thread(target=_copy_socket, args=(right, left), daemon=True),
    )
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def _copy_socket(source: socket.socket, destination: socket.socket) -> None:
    try:
        while True:
            chunk = source.recv(65_536)
            if not chunk:
                break
            destination.sendall(chunk)
    except OSError:
        pass
    finally:
        try:
            destination.shutdown(socket.SHUT_WR)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
