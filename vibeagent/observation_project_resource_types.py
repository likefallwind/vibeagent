from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ProjectManifestItem:
    group: str
    name: str
    value: str


@dataclass(frozen=True)
class ProjectManifest:
    path: str
    kind: str
    ok: bool
    name: str
    version: str
    items: list[ProjectManifestItem]
    item_count: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class ProjectManifestsObservation:
    kind: Literal["project_manifests"]
    ok: bool
    manifests: list[ProjectManifest]
    total_files: int
    scanned_files: int
    total_items: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class ProjectInstructionSource:
    path: str
    scope: str
    bytes: int
    chars: int
    empty: bool
    included: bool
    message: str
    reason: str = "session_start"
    patterns: list[str] = field(default_factory=list)
    owner_path: str | None = None
    parent_path: str | None = None


@dataclass(frozen=True)
class ProjectInstructionsObservation:
    kind: Literal["project_instructions"]
    ok: bool
    files: list[ProjectInstructionSource]
    total_files: int
    scanned_files: int
    omitted_files: int
    truncated: bool
    text: str
    message: str


@dataclass(frozen=True)
class ProjectSkill:
    name: str
    description: str
    path: str
    source: str
    available: bool
    message: str


@dataclass(frozen=True)
class ProjectSkillsObservation:
    kind: Literal["project_skills"]
    ok: bool
    skills: list[ProjectSkill]
    total: int
    truncated: bool
    invalid: int
    message: str


@dataclass(frozen=True)
class ProjectAgentProfile:
    name: str
    description: str
    mode: str
    tools: list[str] | None
    path: str
    source: str
    available: bool
    message: str
    disallowed_tools: list[str] = field(default_factory=list)
    max_turns: int | None = None
    skills: list[str] = field(default_factory=list)
    memory: str | None = None


@dataclass(frozen=True)
class ProjectAgentsObservation:
    kind: Literal["project_agents"]
    ok: bool
    agents: list[ProjectAgentProfile]
    total: int
    truncated: bool
    invalid: int
    message: str


@dataclass(frozen=True)
class SkillObservation:
    kind: Literal["skill"]
    ok: bool
    name: str
    description: str
    path: str
    source: str
    content: str
    bytes: int
    truncated: bool
    max_bytes: int
    message: str
    arguments: str | None = None


@dataclass(frozen=True)
class ProjectTodo:
    path: str
    line: int
    marker: str
    text: str


@dataclass(frozen=True)
class ProjectTodosObservation:
    kind: Literal["project_todos"]
    ok: bool
    todos: list[ProjectTodo]
    total: int
    truncated: bool
    total_files: int
    scanned_files: int
    path: str
    markers: list[str]
    message: str
