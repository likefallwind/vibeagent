from __future__ import annotations

from .project_trust import (
    format_project_trust_report_text,
    get_project_trust_report,
    trust_project_permissions,
    untrust_project_permissions,
)


def get_project_trust_text(root: str = ".") -> str:
    return format_project_trust_report_text(get_project_trust_report(root))


def get_trust_project_report(root: str = ".") -> dict[str, object]:
    return trust_project_permissions(root)


def get_trust_project_text(root: str = ".") -> str:
    return format_project_trust_report_text(get_trust_project_report(root))


def get_untrust_project_report(root: str = ".") -> dict[str, object]:
    return untrust_project_permissions(root)


def get_untrust_project_text(root: str = ".") -> str:
    return format_project_trust_report_text(get_untrust_project_report(root))


__all__ = [
    "format_project_trust_report_text",
    "get_project_trust_report",
    "get_project_trust_text",
    "get_trust_project_report",
    "get_trust_project_text",
    "get_untrust_project_report",
    "get_untrust_project_text",
]
