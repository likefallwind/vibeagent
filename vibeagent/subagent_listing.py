from __future__ import annotations

from .background_delegate_runtime import list_background_delegate_snapshots
from .subagent_transcripts import SubagentTranscriptError, list_subagent_transcripts
from .types import ListAgentsAction, ListAgentsObservation, SubagentInstance
from .workspace_core import RunWorkspace


def execute_list_agents_action(
    workspace: RunWorkspace,
    action: object,
) -> ListAgentsObservation | None:
    if not isinstance(action, ListAgentsAction):
        return None
    return list_session_agents(workspace, action.max_agents)


def list_session_agents(
    workspace: RunWorkspace,
    max_agents: int = 100,
) -> ListAgentsObservation:
    max_agents = max(1, min(max_agents, 500))
    try:
        transcripts, invalid, store_truncated = list_subagent_transcripts(workspace)
    except SubagentTranscriptError as error:
        return ListAgentsObservation(
            kind="list_agents",
            ok=False,
            agents=[],
            total=0,
            truncated=False,
            invalid=0,
            message=str(error),
        )
    by_id = {
        transcript.subagent_id: SubagentInstance(
            id=transcript.subagent_id,
            task=transcript.action.task,
            status=transcript.status,
            mode=transcript.action.mode,
            agent=transcript.action.agent,
            background=transcript.action.run_in_background,
            runs=transcript.runs,
            resumable=transcript.status != "running",
        )
        for transcript in transcripts
    }
    for snapshot in list_background_delegate_snapshots(workspace):
        prior = by_id.get(snapshot.task_id)
        by_id[snapshot.task_id] = SubagentInstance(
            id=snapshot.task_id,
            task=snapshot.action.task,
            status=snapshot.status,
            mode=snapshot.action.mode,
            agent=snapshot.action.agent,
            background=True,
            runs=prior.runs if prior is not None else 1,
            resumable=snapshot.status != "running",
        )
    ordered = sorted(
        by_id.values(),
        key=lambda item: (item.status != "running", item.id),
    )
    total = len(ordered)
    truncated = store_truncated or total > max_agents
    shown = ordered[:max_agents]
    return ListAgentsObservation(
        kind="list_agents",
        ok=True,
        agents=shown,
        total=total,
        truncated=truncated,
        invalid=invalid,
        message=f"Listed {len(shown)}/{total} session subagent instance(s); invalid transcripts: {invalid}.",
    )


__all__ = ["execute_list_agents_action", "list_session_agents"]
