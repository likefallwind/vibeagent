from __future__ import annotations

import unicodedata


_SHORT_ESCAPES = {
    "\a": r"\a",
    "\b": r"\b",
    "\t": r"\t",
    "\n": r"\n",
    "\v": r"\v",
    "\f": r"\f",
    "\r": r"\r",
}
_UNSAFE_UNICODE_CATEGORIES = {"Cc", "Cf", "Cs", "Zl", "Zp"}


def terminal_safe_text(value: str) -> str:
    """Make terminal controls and invisible formatting characters explicit."""
    if not any(_requires_escape(character) for character in value):
        return value
    return "[escaped] " + "".join(_escaped_character(character) for character in value)


def normalized_shell_permission_subject(value: str) -> str:
    """Collapse shell whitespace for conservative deny and ask rule matching."""
    translated = value.strip(" \t\r\n\f\v").translate(_SHELL_WHITESPACE)
    return " ".join(part for part in translated.split(" ") if part)


def _requires_escape(character: str) -> bool:
    return unicodedata.category(character) in _UNSAFE_UNICODE_CATEGORIES


def _escaped_character(character: str) -> str:
    if character == "\\":
        return r"\\"
    if character in _SHORT_ESCAPES:
        return _SHORT_ESCAPES[character]
    if not _requires_escape(character):
        return character
    codepoint = ord(character)
    if codepoint <= 0xFF:
        return f"\\x{codepoint:02x}"
    if codepoint <= 0xFFFF:
        return f"\\u{codepoint:04x}"
    return f"\\U{codepoint:08x}"


_SHELL_WHITESPACE = str.maketrans({
    "\t": " ",
    "\r": " ",
    "\n": " ",
    "\f": " ",
    "\v": " ",
})


__all__ = ["normalized_shell_permission_subject", "terminal_safe_text"]
