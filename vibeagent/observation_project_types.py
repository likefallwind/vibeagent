from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .observation_project_check_types import (
    CheckSuggestedChecksObservation,
    RunSuggestedChecksObservation,
    SuggestChecksObservation,
    SuggestedCheck,
)
from .observation_project_command_types import (
    ProjectCommand,
    ProjectCommandsObservation,
    ToolSearchObservation,
)
from .observation_project_test_types import (
    CheckFocusedTestCommandsObservation,
    FocusedTestCommand,
    FocusedTestCommandsObservation,
    RelatedTestCandidate,
    RelatedTestsObservation,
    RunFocusedTestCommandsObservation,
)
from .observation_project_resource_types import (
    ProjectAgentProfile,
    ProjectAgentsObservation,
    ProjectInstructionSource,
    ProjectInstructionsObservation,
    ProjectManifest,
    ProjectManifestItem,
    ProjectManifestsObservation,
    ProjectSkill,
    ProjectSkillsObservation,
    ProjectTodo,
    ProjectTodosObservation,
    SkillObservation,
)
from .observation_runtime_types import RuntimeToolInfo


@dataclass(frozen=True)
class ProjectOverviewObservation:
    kind: Literal["project_overview"]
    ok: bool
    project_root: str
    is_git_repo: bool
    git_branch: str
    git_head: str
    git_upstream: str
    git_ahead: int
    git_behind: int
    git_status: str
    tree: list[str]
    files: list[str]
    total_tree_entries: int
    total_files: int
    repo_truncated: bool
    commands: list[ProjectCommand]
    commands_total: int
    commands_truncated: bool
    manifests: list[ProjectManifest]
    manifest_files_total: int
    manifests_truncated: bool
    instruction_sources: list[ProjectInstructionSource]
    instruction_files_total: int
    instructions_truncated: bool
    todos: list[ProjectTodo]
    todos_total: int
    todos_truncated: bool
    suggested_checks: list[SuggestedCheck]
    suggested_checks_total: int
    suggested_checks_truncated: bool
    skills: list[ProjectSkill]
    skills_total: int
    skills_truncated: bool
    tools: list[RuntimeToolInfo]
    message: str
