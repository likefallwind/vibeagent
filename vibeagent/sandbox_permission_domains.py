from __future__ import annotations

from .sandbox_network_policy import normalize_sandbox_domain
from .workspace_permissions import ProjectPermissions


def sandbox_webfetch_allow_domains(
    permissions: ProjectPermissions,
    *,
    project_config_trusted: bool,
    managed_only: bool,
) -> tuple[str, ...]:
    domains: list[str] = []
    trusted_sources = frozenset(permissions.trusted_allow_sources)
    for rule in permissions.rules:
        if rule.effect != "allow" or rule.tool.lower() not in {
            "webfetch",
            "web_fetch",
        }:
            continue
        if managed_only and not rule.managed:
            continue
        if not (
            rule.managed
            or permissions.allow_rules_trusted
            or project_config_trusted
            or rule.source in trusted_sources
        ):
            continue
        specifier = rule.specifier or ""
        if not specifier.startswith("domain:"):
            continue
        value = specifier.removeprefix("domain:").strip()
        try:
            domain = normalize_sandbox_domain(value, field="WebFetch allow rule")
        except ValueError:
            continue
        if domain not in domains:
            domains.append(domain)
    return tuple(domains)


__all__ = ["sandbox_webfetch_allow_domains"]
