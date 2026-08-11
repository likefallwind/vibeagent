from __future__ import annotations

from contextlib import AbstractContextManager
import os
import select
import shutil
import sys
import time
from typing import Protocol


class AgentViewTerminal(Protocol):
    def __enter__(self) -> AgentViewTerminal: ...

    def __exit__(self, *_args: object) -> None: ...

    def size(self) -> tuple[int, int]: ...

    def draw(self, lines: list[str]) -> None: ...

    def read_key(self, timeout: float) -> str | None: ...

    def prompt(self, label: str) -> str | None: ...


class StandardAgentViewTerminal(AbstractContextManager["StandardAgentViewTerminal"]):
    def __init__(self) -> None:
        self._unix_attributes = None
        self._active = False

    def __enter__(self) -> StandardAgentViewTerminal:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ValueError("Agent view requires an interactive terminal.")
        self._enter_screen()
        return self

    def __exit__(self, *_args: object) -> None:
        self._leave_screen()

    def size(self) -> tuple[int, int]:
        size = shutil.get_terminal_size((100, 30))
        return size.columns, size.lines

    def draw(self, lines: list[str]) -> None:
        width, height = self.size()
        body = "\n".join(line[:width] for line in lines[:height])
        sys.stdout.write("\x1b[H\x1b[2J" + body)
        sys.stdout.flush()

    def read_key(self, timeout: float) -> str | None:
        if os.name == "nt":
            return self._read_windows_key(timeout)
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            return None
        value = os.read(sys.stdin.fileno(), 1).decode("utf-8", errors="ignore")
        if value in {"\x03", "\x04"}:
            return "q"
        if value != "\x1b":
            return {"\r": "enter", "\n": "enter", " ": "space"}.get(value, value)
        ready, _, _ = select.select([sys.stdin], [], [], 0.01)
        if not ready:
            return "escape"
        suffix = os.read(sys.stdin.fileno(), 2).decode("ascii", errors="ignore")
        return {
            "[A": "up",
            "[B": "down",
            "[C": "right",
            "[D": "left",
            "[H": "home",
            "[F": "end",
        }.get(suffix, "escape")

    def prompt(self, label: str) -> str | None:
        self._leave_screen()
        try:
            return input(label)
        except (EOFError, KeyboardInterrupt):
            return None
        finally:
            self._enter_screen()

    def _enter_screen(self) -> None:
        if self._active:
            return
        try:
            if os.name != "nt":
                import termios
                import tty

                descriptor = sys.stdin.fileno()
                self._unix_attributes = termios.tcgetattr(descriptor)
                tty.setcbreak(descriptor)
            sys.stdout.write("\x1b[?1049h\x1b[?25l")
            sys.stdout.flush()
            self._active = True
        except BaseException:
            if os.name != "nt" and self._unix_attributes is not None:
                import termios

                termios.tcsetattr(
                    sys.stdin.fileno(),
                    termios.TCSADRAIN,
                    self._unix_attributes,
                )
                self._unix_attributes = None
            raise

    def _leave_screen(self) -> None:
        if not self._active:
            return
        if os.name != "nt" and self._unix_attributes is not None:
            import termios

            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._unix_attributes)
            self._unix_attributes = None
        sys.stdout.write("\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
        self._active = False

    @staticmethod
    def _read_windows_key(timeout: float) -> str | None:
        import msvcrt

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not msvcrt.kbhit():
                time.sleep(0.01)
                continue
            value = msvcrt.getwch()
            if value in {"\x00", "\xe0"}:
                return {
                    "H": "up",
                    "P": "down",
                    "M": "right",
                    "K": "left",
                    "G": "home",
                    "O": "end",
                }.get(msvcrt.getwch())
            return {
                "\r": "enter",
                " ": "space",
                "\x1b": "escape",
                "\x03": "q",
                "\x04": "q",
            }.get(value, value)
        return None


__all__ = ["AgentViewTerminal", "StandardAgentViewTerminal"]
