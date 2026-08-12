from __future__ import annotations

from ipaddress import ip_address
import re


MAX_SANDBOX_DOMAINS = 200
_DOMAIN_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


def normalize_sandbox_domain(value: str, *, field: str) -> str:
    candidate = value.strip().lower()
    wildcard = candidate.startswith("*.")
    hostname = candidate[2:] if wildcard else candidate
    if not hostname or hostname.endswith(".") or any(char in hostname for char in "/:@?#[]"):
        raise ValueError(f"sandbox.network.{field} contains an invalid domain: {value}")
    try:
        normalized = hostname.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise ValueError(
            f"sandbox.network.{field} contains an invalid domain: {value}"
        ) from error
    if len(normalized) > 253:
        raise ValueError(f"sandbox.network.{field} contains an invalid domain: {value}")
    try:
        ip_address(normalized)
    except ValueError:
        if any(
            _DOMAIN_LABEL.fullmatch(label) is None for label in normalized.split(".")
        ):
            raise ValueError(f"sandbox.network.{field} contains an invalid domain: {value}")
    else:
        if wildcard:
            raise ValueError(f"sandbox.network.{field} cannot wildcard an IP address: {value}")
    return f"*.{normalized}" if wildcard else normalized


def normalize_sandbox_domains(values: list[str], *, field: str) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(normalize_sandbox_domain(value, field=field) for value in values))
    if len(normalized) > MAX_SANDBOX_DOMAINS:
        raise ValueError(
            f"sandbox.network.{field} exceeds {MAX_SANDBOX_DOMAINS} entries."
        )
    return normalized


def sandbox_domain_matches(hostname: str, pattern: str) -> bool:
    try:
        normalized = hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError:
        return False
    if pattern.startswith("*."):
        suffix = pattern[2:]
        return normalized != suffix and normalized.endswith(f".{suffix}")
    return normalized == pattern


def sandbox_domain_allowed(
    hostname: str,
    allowed_domains: tuple[str, ...],
    denied_domains: tuple[str, ...],
) -> bool:
    if any(sandbox_domain_matches(hostname, pattern) for pattern in denied_domains):
        return False
    return any(sandbox_domain_matches(hostname, pattern) for pattern in allowed_domains)


__all__ = [
    "MAX_SANDBOX_DOMAINS",
    "normalize_sandbox_domain",
    "normalize_sandbox_domains",
    "sandbox_domain_allowed",
    "sandbox_domain_matches",
]
