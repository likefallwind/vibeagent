from __future__ import annotations

from .agent_observation_utils import summarize
from .types import Observation


SESSION_RECOVERY_COMPLETION_KINDS = frozenset({"session_summary", "session_audit", "session_handoff"})
SESSION_RECOVERY_COMPLETION_DETAIL_FIELDS = (
    ("latest_completion_pending_verification_checks", "pendingVerificationChecks"),
    ("latest_completion_failed_verification_checks", "failedVerificationChecks"),
    ("latest_completion_final_review_issues", "finalReviewBlockingIssues"),
    ("latest_completion_final_review_changed_files", "finalReviewChangedFiles"),
    ("latest_completion_tool_errors", "toolErrors"),
    ("latest_completion_checkpoint_failures", "checkpointFailures"),
    ("latest_completion_active_background_processes", "activeBackgroundProcesses"),
    ("latest_completion_denied_approvals", "deniedApprovals"),
    ("latest_completion_next_actions", "nextActions"),
)


def build_session_recovery_completion_blockers(observations: list[Observation]) -> list[str]:
    observation = latest_unresolved_session_recovery_completion_observation(observations)
    if observation is None:
        return []
    labels = session_recovery_completion_blocker_labels(observation)
    if not labels:
        return ["Recovered session reports completion is not ready."]
    return [f"Recovered session reports completion blocker(s): {summarize('; '.join(labels[:3]), 240)}"]


def build_session_recovery_completion_details(observations: list[Observation]) -> dict[str, list[str]]:
    observation = latest_unresolved_session_recovery_completion_observation(observations)
    if observation is None:
        return {}
    details: dict[str, list[str]] = {}
    for attr, key in SESSION_RECOVERY_COMPLETION_DETAIL_FIELDS:
        values = getattr(observation, attr, [])
        if not isinstance(values, list):
            continue
        labels = [str(value).strip() for value in values if isinstance(value, str) and value.strip()]
        if labels:
            details[key] = labels
    return details


def latest_unresolved_session_recovery_completion_observation(observations: list[Observation]) -> Observation | None:
    for observation in reversed(observations):
        if session_recovery_ready_observation(observation):
            return None
        if observation.kind not in SESSION_RECOVERY_COMPLETION_KINDS:
            continue
        if getattr(observation, "completion_ready", None) is not False:
            continue
        return observation
    return None


def session_recovery_ready_observation(observation: Observation) -> bool:
    if observation.kind == "final_review" and getattr(observation, "ready", None) is True:
        return True
    if observation.kind not in {"session_verification", "session_audit", "session_handoff"}:
        return False
    if getattr(observation, "ready", None) is True:
        return True
    status = str(getattr(observation, "status", "") or "").strip().casefold()
    return status == "ready"


def session_recovery_completion_blocker_labels(observation: Observation) -> list[str]:
    labels: list[str] = []
    for attr in ("completion_blockers", "latest_completion_blockers"):
        values = getattr(observation, attr, [])
        if not isinstance(values, list):
            continue
        labels.extend(str(value).strip() for value in values if isinstance(value, str) and value.strip())
    return labels
