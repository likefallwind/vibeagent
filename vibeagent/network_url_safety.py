from __future__ import annotations

import ipaddress
import socket
import urllib.request
from typing import Literal
from urllib.parse import urlparse


UrlScope = Literal["local", "public"]


class UrlSafetyError(ValueError):
    pass


def validate_scoped_url(url: str, scope: UrlScope) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UrlSafetyError("URL must use HTTP or HTTPS and include a host.")
    if parsed.username is not None or parsed.password is not None:
        raise UrlSafetyError("URL credentials are not allowed.")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as error:
        raise UrlSafetyError(f"URL has an invalid port: {error}.") from error

    addresses = _resolve_addresses(parsed.hostname, port)
    if not addresses:
        raise UrlSafetyError(f"URL host {parsed.hostname!r} did not resolve to an IP address.")
    invalid = [address for address in addresses if not _address_allowed(address, scope)]
    if invalid:
        expected = "local or private" if scope == "local" else "public"
        rendered = ", ".join(str(address) for address in invalid)
        raise UrlSafetyError(f"URL host must resolve only to {expected} addresses; rejected: {rendered}.")


def open_scoped_url(
    request: urllib.request.Request,
    *,
    timeout: float,
    scope: UrlScope,
):
    validate_scoped_url(request.full_url, scope)
    opener = urllib.request.build_opener(_ScopedRedirectHandler(scope))
    return opener.open(request, timeout=timeout)


def _resolve_addresses(host: str, port: int) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        return {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
    except (socket.gaierror, ValueError) as error:
        raise UrlSafetyError(f"Could not resolve URL host {host!r}: {error}.") from error


def _address_allowed(address: ipaddress.IPv4Address | ipaddress.IPv6Address, scope: UrlScope) -> bool:
    if scope == "public":
        return address.is_global
    return address.is_loopback or address.is_private or address.is_link_local


class _ScopedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, scope: UrlScope) -> None:
        self.scope = scope

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        validate_scoped_url(newurl, self.scope)
        return super().redirect_request(req, fp, code, msg, headers, newurl)
