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
            isolation=transcript.action.isolation,
            worktree_path=transcript.worktree.project_path if transcript.worktree is not None else None,
            worktree_branch=transcript.worktree.branch if transcript.worktree is not None else None,
            worktree_preserved=transcript.worktree.preserved if transcript.worktree is not None else False,
            depth=transcript.depth,
            parent_id=transcript.parent_id,
            teammate_name=transcript.action.teammate_name,
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
            isolation=snapshot.action.isolation,
            worktree_path=prior.worktree_path if prior is not None else None,
            worktree_branch=prior.worktree_branch if prior is not None else None,
            worktree_preserved=(prior.worktree_preserved if prior is not None else snapshot.action.isolation == "worktree"),
            depth=prior.depth if prior is not None else snapshot.depth,
            parent_id=prior.parent_id if prior is not None else snapshot.parent_id,
            teammate_name=snapshot.action.teammate_name,
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
