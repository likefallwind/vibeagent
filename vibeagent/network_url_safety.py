from __future__ import annotations

import ipaddress
import socket
import urllib.request
from typing import Literal
from urllib.parse import urlparse


UrlScope = Literal["local", "public"]


class UrlSafetyError(ValueError):
    pass


def validate_scoped_url(url: str, scope: UrlScope, *, require_https: bool = False) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UrlSafetyError("URL must use HTTP or HTTPS and include a host.")
    if require_https and parsed.scheme != "https":
        raise UrlSafetyError("URL and redirects must use HTTPS.")
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
    require_https: bool = False,
    use_environment_proxy: bool = True,
):
    validate_scoped_url(request.full_url, scope, require_https=require_https)
    handlers: list[object] = [
        _ScopedRedirectHandler(scope, require_https=require_https)
    ]
    if not use_environment_proxy:
        handlers.insert(0, urllib.request.ProxyHandler({}))
    opener = urllib.request.build_opener(*handlers)
    return opener.open(request, timeout=timeout)


def open_local_or_public_url(
    request: urllib.request.Request,
    *,
    timeout: float,
):
    """Open a URL while preventing redirects across local/public trust scopes."""
    local_error: UrlSafetyError | None = None
    try:
        validate_scoped_url(request.full_url, "local")
        scope: UrlScope = "local"
    except UrlSafetyError as error:
        local_error = error
        try:
            validate_scoped_url(request.full_url, "public")
            scope = "public"
        except UrlSafetyError:
            raise local_error
    return open_scoped_url(
        request,
        timeout=timeout,
        scope=scope,
        use_environment_proxy=False,
    )


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
    def __init__(self, scope: UrlScope, *, require_https: bool = False) -> None:
        self.scope = scope
        self.require_https = require_https

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        validate_scoped_url(newurl, self.scope, require_https=self.require_https)
        return super().redirect_request(req, fp, code, msg, headers, newurl)
