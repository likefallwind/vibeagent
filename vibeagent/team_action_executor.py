from __future__ import annotations

from .action_team_types import TeamCreateAction, TeamDeleteAction
from .agent_runtime_utils import append_session_event
from .background_delegate_runtime import list_background_delegate_snapshots
from .observation_team_types import TeamCreateObservation, TeamDeleteObservation
from .team_state import TeamStateError, create_team_state, delete_team_state, read_team_state
from .workspace_core import RunWorkspace


def execute_team_action(workspace: RunWorkspace, action: object) -> object | None:
    if isinstance(action, TeamCreateAction):
        return _create_team(workspace, action)
    if isinstance(action, TeamDeleteAction):
        return _delete_team(workspace)
    return None


def _create_team(workspace: RunWorkspace, action: TeamCreateAction) -> TeamCreateObservation:
    from .agent_team_runtime import agent_teams_enabled

    if not agent_teams_enabled():
        return TeamCreateObservation(
            kind="team_create",
            ok=False,
            team_name=None,
            description=action.description,
            message="Agent teams are disabled. Set CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 to enable them.",
        )
    try:
        state = create_team_state(
            workspace,
            action.team_name,
            action.description,
            explicit=True,
        )
    except (OSError, TeamStateError) as error:
        return TeamCreateObservation(
            kind="team_create",
            ok=False,
            team_name=None,
            description=action.description,
            message=str(error),
        )
    append_session_event(
        workspace.session_dir,
        "team_created",
        {"team_name": state.name, "explicit": True},
    )
    return TeamCreateObservation(
        kind="team_create",
        ok=True,
        team_name=state.name,
        description=state.description,
        message=f"Created agent team {state.name}. Spawn named teammates with Agent.",
    )


def _delete_team(workspace: RunWorkspace) -> TeamDeleteObservation:
    from .agent_team_runtime import agent_teams_enabled, clear_team_messages

    if not agent_teams_enabled():
        return TeamDeleteObservation(
            kind="team_delete",
            ok=False,
            team_name=None,
            message="Agent teams are disabled. Set CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 to enable them.",
        )
    try:
        state = read_team_state(workspace)
    except (OSError, TeamStateError) as error:
        return TeamDeleteObservation(kind="team_delete", ok=False, team_name=None, message=str(error))
    if state is None:
        return TeamDeleteObservation(
            kind="team_delete",
            ok=False,
            team_name=None,
            message="No agent team exists in this session.",
        )
    active = sorted(
        snapshot.action.teammate_name
        for snapshot in list_background_delegate_snapshots(workspace)
        if snapshot.status == "running" and snapshot.action.teammate_name is not None
    )
    if active:
        return TeamDeleteObservation(
            kind="team_delete",
            ok=False,
            team_name=state.name,
            active_teammates=active,
            message=f"Cannot delete team {state.name} while teammate(s) are running: {', '.join(active)}.",
        )
    try:
        delete_team_state(workspace)
    except (OSError, TeamStateError) as error:
        return TeamDeleteObservation(
            kind="team_delete", ok=False, team_name=state.name, message=str(error)
        )
    clear_team_messages(workspace)
    append_session_event(workspace.session_dir, "team_deleted", {"team_name": state.name})
    return TeamDeleteObservation(
        kind="team_delete",
        ok=True,
        team_name=state.name,
        message=f"Deleted agent team {state.name} and cleared its coordination state.",
    )


__all__ = ["execute_team_action"]
