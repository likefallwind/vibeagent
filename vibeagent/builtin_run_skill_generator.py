from __future__ import annotations

import json
import shlex

from .builtin_workflow_types import BuiltinModelWorkflow


def build_run_skill_generator_workflow(
    argument: str | None,
    *,
    interactive: bool,
) -> BuiltinModelWorkflow:
    app_hint = parse_run_skill_generator_hint(argument)
    selection_instruction = (
        "If several runnable apps remain plausible, call ask_user with the concrete candidates before running commands or writing files."
        if interactive
        else "If several runnable apps remain plausible, stop with the concrete candidates and require an explicit app hint; do not guess or write files in print mode."
    )
    return BuiltinModelWorkflow(
        task="\n".join(
            [
                "Run the built-in project run-skill generator.",
                f"Application or package hint: {json.dumps(app_hint or 'not provided')}",
                "Inspect project instructions, manifests, documented commands, repository structure, and project_skills. Identify the app entry point, package cwd, runtime type, prerequisites, and any existing verify or run-* skill before taking side effects.",
                selection_instruction,
                "Choose a stable lowercase hyphenated skill name run-<app> using at most 64 characters. The destination must be exactly .claude/skills/<name>/SKILL.md at the repository root; encode a monorepo package in the name, description, and Scope section rather than writing an undiscoverable nested skill. Never write a personal skill or an .agents skill.",
                "Establish a clean launch context: record existing processes, do not reuse a pre-existing app process as evidence, use the documented project or package cwd, and depend only on declared prerequisites and named environment variables. Never delete dependency trees, reset Git state, expose secret values, or open a GUI through a shell command.",
                "Derive the install or preparation, build, launch, readiness, drive, observation, and cleanup steps. Preflight every command. Execute the real build and entry point, wait for readiness, then exercise externally observable behavior appropriate to the runtime: representative CLI input/output, HTTP/API requests, TUI interaction, or a browser-capable skill or MCP tool for UI flows.",
                "Do not record guessed executable steps. Every build, launch, readiness, drive, and cleanup command included in the recipe must be supported by evidence from this run. If browser interaction is required but unavailable, record that limitation explicitly and do not claim the visual flow was validated.",
                "Stop only processes started by this workflow, using check_stop_process before stop_process. Inspect output after the driven interaction and confirm cleanup before writing the recipe.",
                "Write one concise SKILL.md with YAML frontmatter containing name matching the directory and a specific description. Its body must include Scope, Prerequisites, Prepare, Build, Launch, Readiness, Drive, Observe, Cleanup, and Failure recovery sections with exact relative cwd values, commands, expected evidence, environment variable names with placeholders, and process ownership rules.",
                "Do not include credentials, secret values, captured application data, machine-specific absolute paths, volatile process IDs or ports unless the port is a stable project contract. Do not add allowed-tools or relax permissions; future runs must retain normal approvals.",
                "If the destination already exists, load it first and preserve validated steps. Change it only for commands or omissions this run proved wrong; do not rewrite it for wording or formatting alone.",
                "After writing, call project_skills and then skill with the exact generated name. Require the skill to be available from the intended project path with the expected content; treat shadowing, invalid frontmatter, truncation, or load failure as a failed generation and fix it before finishing.",
                "Run final_review for the new or changed skill. Finish with the skill path plus a compact evidence table for build, launch, readiness, driven behavior, observation, cleanup, and reload. Mark any unavailable UI interaction as UNVERIFIED and never call the recipe complete unless every required criterion is PASS.",
            ]
        ),
        metadata={
            "source": "builtin_command",
            "name": "run-skill-generator",
            "arguments": argument or "",
            "app_hint": app_hint,
            "interactive": interactive,
        },
    )


def parse_run_skill_generator_hint(argument: str | None) -> str | None:
    try:
        tokens = shlex.split(argument or "")
    except ValueError as error:
        raise ValueError(f"/run-skill-generator arguments are invalid: {error}") from error

    hint_parts: list[str] = []
    options = True
    for token in tokens:
        if options and token == "--":
            options = False
        elif options and token.startswith("-"):
            raise ValueError(f"Unknown /run-skill-generator option: {token}")
        else:
            hint_parts.append(token)
    hint = " ".join(hint_parts).strip() or None
    if hint is not None and (len(hint) > 1_000 or "\x00" in hint):
        raise ValueError("/run-skill-generator hint must contain at most 1000 characters and no NUL.")
    return hint


__all__ = ["build_run_skill_generator_workflow", "parse_run_skill_generator_hint"]
