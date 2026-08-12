from __future__ import annotations


MASKED_CREDENTIAL = b"[MASKED_CREDENTIAL]"


class StreamingCredentialRedactor:
    def __init__(self, secrets: list[bytes] | tuple[bytes, ...]) -> None:
        self._secrets = tuple(
            sorted({secret for secret in secrets if secret}, key=len, reverse=True)
        )
        self._pending = bytearray()

    def feed(self, value: bytes, *, final: bool = False) -> bytes:
        self._pending.extend(value)
        output = bytearray()
        while self._pending:
            match = self._leftmost_match()
            if match is not None:
                index, secret = match
                if not final and self._could_extend(index):
                    output.extend(self._pending[:index])
                    del self._pending[:index]
                    break
                output.extend(self._pending[:index])
                output.extend(MASKED_CREDENTIAL)
                del self._pending[: index + len(secret)]
                continue
            if final:
                output.extend(self._pending)
                self._pending.clear()
                break
            keep = self._longest_secret_prefix_suffix()
            emit = len(self._pending) - keep
            output.extend(self._pending[:emit])
            del self._pending[:emit]
            break
        return bytes(output)

    def _leftmost_match(self) -> tuple[int, bytes] | None:
        selected: tuple[int, bytes] | None = None
        pending = bytes(self._pending)
        for secret in self._secrets:
            index = pending.find(secret)
            if index < 0:
                continue
            if selected is None or index < selected[0] or (
                index == selected[0] and len(secret) > len(selected[1])
            ):
                selected = index, secret
        return selected

    def _could_extend(self, index: int) -> bool:
        suffix = bytes(self._pending[index:])
        return any(
            len(candidate) > len(suffix) and candidate.startswith(suffix)
            for candidate in self._secrets
        )

    def _longest_secret_prefix_suffix(self) -> int:
        pending = bytes(self._pending)
        maximum = min(len(pending), max((len(secret) for secret in self._secrets), default=0))
        for size in range(maximum, 0, -1):
            suffix = pending[-size:]
            if any(secret.startswith(suffix) for secret in self._secrets):
                return size
        return 0


__all__ = ["MASKED_CREDENTIAL", "StreamingCredentialRedactor"]
