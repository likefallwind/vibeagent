from __future__ import annotations

import os

from .background_delegate_runtime import list_background_delegate_snapshots
from .subagent_transcripts import SubagentTranscriptError, list_subagent_transcripts
from .types import ListAgentsAction, ListAgentsObservation, SubagentInstance
from .peer_registry import list_peer_sessions
from .peer_types import PeerMessagingError
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
        peers, invalid_peers = list_peer_sessions()
        peers = [
            peer
            for peer in peers
            if not (peer.pid == os.getpid() and peer.run_id == workspace.run_id)
        ]
    except (OSError, PeerMessagingError):
        peers, invalid_peers = [], 0
    try:
        transcripts, invalid, store_truncated = list_subagent_transcripts(workspace)
    except SubagentTranscriptError as error:
        return ListAgentsObservation(
            kind="list_agents",
            ok=False,
            agents=[],
            total=len(peers),
            truncated=len(peers) > max_agents,
            invalid=invalid_peers,
            message=f"{error} Listed {min(len(peers), max_agents)}/{len(peers)} peer session(s).",
            peers=peers[:max_agents],
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
            color=transcript.action.color,
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
            color=snapshot.action.color,
        )
    ordered = sorted(
        by_id.values(),
        key=lambda item: (item.status != "running", item.id),
    )
    total = len(ordered) + len(peers)
    combined = [("subagent", item) for item in ordered] + [("peer", item) for item in peers]
    truncated = store_truncated or total > max_agents
    shown_pairs = combined[:max_agents]
    shown = [item for kind, item in shown_pairs if kind == "subagent"]
    shown_peers = [item for kind, item in shown_pairs if kind == "peer"]
    return ListAgentsObservation(
        kind="list_agents",
        ok=True,
        agents=shown,
        total=total,
        truncated=truncated,
        invalid=invalid + invalid_peers,
        message=(
            f"Listed {len(shown_pairs)}/{total} reachable agent(s): {len(shown)} subagent(s), "
            f"{len(shown_peers)} peer session(s); invalid records: {invalid + invalid_peers}."
        ),
        peers=shown_peers,
    )


__all__ = ["execute_list_agents_action", "list_session_agents"]
