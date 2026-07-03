from __future__ import annotations

import codecs
from pathlib import Path


def truncate_utf8_text_bytes(content: str, max_bytes: int) -> str:
    return content.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")


def read_utf8_text_file(path: Path, relative_path: str) -> str:
    if detect_binary_file(path):
        raise ValueError(f"File appears to be binary or non-UTF-8 text: {relative_path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"File is not valid UTF-8 text: {relative_path}") from error


def parse_image_header(data: bytes) -> tuple[str | None, str | None, int | None, int | None]:
    if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR":
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        return "png", "image/png", width, height

    if len(data) >= 10 and data[:6] in {b"GIF87a", b"GIF89a"}:
        width = int.from_bytes(data[6:8], "little")
        height = int.from_bytes(data[8:10], "little")
        return "gif", "image/gif", width, height

    if len(data) >= 4 and data.startswith(b"\xff\xd8"):
        width, height = parse_jpeg_dimensions(data)
        return "jpeg", "image/jpeg", width, height

    if len(data) >= 30 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        width, height = parse_webp_dimensions(data)
        return "webp", "image/webp", width, height

    return None, None, None, None


def parse_jpeg_dimensions(data: bytes) -> tuple[int | None, int | None]:
    index = 2
    sof_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while index + 4 <= len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        while index < len(data) and data[index] == 0xFF:
            index += 1
        if index >= len(data):
            break
        marker = data[index]
        index += 1
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if index + 2 > len(data):
            break
        segment_length = int.from_bytes(data[index : index + 2], "big")
        if segment_length < 2 or index + segment_length > len(data):
            break
        if marker in sof_markers and segment_length >= 7:
            height = int.from_bytes(data[index + 3 : index + 5], "big")
            width = int.from_bytes(data[index + 5 : index + 7], "big")
            return width, height
        index += segment_length
    return None, None


def parse_webp_dimensions(data: bytes) -> tuple[int | None, int | None]:
    chunk = data[12:16]
    if chunk == b"VP8X" and len(data) >= 30:
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return width, height
    if chunk == b"VP8 " and len(data) >= 30 and data[23:26] == b"\x9d\x01\x2a":
        width = int.from_bytes(data[26:28], "little") & 0x3FFF
        height = int.from_bytes(data[28:30], "little") & 0x3FFF
        return width, height
    if chunk == b"VP8L" and len(data) >= 25 and data[20] == 0x2F:
        bits = int.from_bytes(data[21:25], "little")
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return width, height
    return None, None


def detect_binary_file(path: Path, sample_bytes: int = 4096) -> bool:
    with path.open("rb") as handle:
        sample = handle.read(sample_bytes)
    if b"\0" in sample:
        return True
    try:
        decoder = codecs.getincrementaldecoder("utf-8")()
        decoder.decode(sample, final=False)
    except UnicodeDecodeError:
        return True
    return False


def count_file_lines(path: Path) -> int:
    count = 0
    has_bytes = False
    ends_with_newline = False
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if chunk:
                has_bytes = True
                count += chunk.count(b"\n")
                ends_with_newline = chunk.endswith(b"\n")
    if has_bytes and not ends_with_newline:
        count += 1
    return count


def format_line_excerpt(content: str, start_line: int, line_count: int) -> str:
    if start_line < 1:
        raise ValueError("start_line must be at least 1.")
    if line_count < 1:
        raise ValueError("line_count must be at least 1.")
    if line_count > 1000:
        raise ValueError("line_count must be at most 1000.")

    lines = content.splitlines()
    start_index = start_line - 1
    end_index = min(start_index + line_count, len(lines))
    if start_index >= len(lines):
        return ""
    return format_numbered_lines("\n".join(lines[start_index:end_index]), start_line=start_line)


def format_numbered_lines(content: str, start_line: int = 1) -> str:
    return "\n".join(
        f"{line_number}: {line}"
        for line_number, line in enumerate(content.splitlines(), start=start_line)
    )
