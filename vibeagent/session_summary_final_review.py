from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .session_summary_helpers import session_changed_file_labels, session_check_failure_labels
from .session_utils import as_int


@dataclass
class SessionFinalReviewSummary:
    ready: bool | None = None
    blocking_issues: int = 0
    warnings: int = 0
    files: int = 0
    changed_files: list[str] = field(default_factory=list)
    suggested_checks: int = 0
    message: str | None = None
    python_failures: list[str] = field(default_factory=list)
    config_failures: list[str] = field(default_factory=list)


def parse_final_review_summary(result: dict[str, Any]) -> SessionFinalReviewSummary:
    ready = result.get("ready")
    total_files = as_int(result.get("total_files"))
    total_checks = as_int(result.get("suggested_checks_total"))
    review_message = result.get("message")
    return SessionFinalReviewSummary(
        ready=ready if isinstance(ready, bool) else None,
        blocking_issues=len(result["blocking_issues"]) if isinstance(result.get("blocking_issues"), list) else 0,
        warnings=len(result["warnings"]) if isinstance(result.get("warnings"), list) else 0,
        files=total_files if total_files is not None else len(result["files"]) if isinstance(result.get("files"), list) else 0,
        changed_files=session_changed_file_labels(result.get("files")),
        suggested_checks=(
            total_checks
            if total_checks is not None
            else len(result["suggested_checks"])
            if isinstance(result.get("suggested_checks"), list)
            else 0
        ),
        message=review_message if isinstance(review_message, str) and review_message.strip() else None,
        python_failures=session_check_failure_labels(result.get("python")),
        config_failures=session_check_failure_labels(result.get("config")),
    )
