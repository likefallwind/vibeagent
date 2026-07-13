from __future__ import annotations

from pathlib import Path

from .workspace_agents import format_project_agent_catalog as _format_project_agent_catalog
from .workspace_core import create_local_workspace as _create_local_workspace
from .workspace_skills import format_project_skill_catalog as _format_project_skill_catalog


def get_agents_text(root: str | Path = ".", max_agents: int = 20) -> str:
    workspace = _create_local_workspace(root, "local-agents")
    return _format_project_agent_catalog(workspace, max_agents=max_agents) or "No project agent profiles found."


def get_skills_text(root: str | Path = ".", max_skills: int = 20) -> str:
    workspace = _create_local_workspace(root, "local-skills")
    return _format_project_skill_catalog(workspace, max_skills=max_skills) or "No project skills found."
