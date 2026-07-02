from __future__ import annotations

from typing import Any


GIT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
{
        "name": "git_status",
        "description": "Read git status in short format for the current project.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
{
        "name": "git_conflicts",
        "description": "Scan for merge/rebase conflicts by reading unmerged git index entries and conflict marker lines in project text files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative file or directory to scan."},
                "max_markers": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum conflict marker entries to return. Defaults to 200.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10000,
                    "description": "Maximum project text files to scan for conflict markers. Defaults to 5000.",
                },
            },
            "additionalProperties": False,
        },
    },
{
        "name": "git_info",
        "description": "Read git repository identity and collaboration state: branch, HEAD, upstream, ahead/behind counts, remotes, and short status. Does not fetch from the network.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
{
        "name": "git_changes",
        "description": "Read a structured summary of changed git files, including status and staged/unstaged insertion/deletion counts.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
{
        "name": "git_branches",
        "description": "List local git branches and the current branch without fetching from the network.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_branches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum local branch count to return. Defaults to 100.",
                },
            },
            "additionalProperties": False,
        },
    },
{
        "name": "check_git_fetch",
        "description": "Validate which git remote would be fetched and report current ahead/behind state without contacting the remote.",
        "input_schema": {
            "type": "object",
            "properties": {
                "remote": {
                    "type": "string",
                    "description": "Remote name to fetch, such as origin. If omitted, the single configured remote is selected.",
                },
            },
            "additionalProperties": False,
        },
    },
{
        "name": "git_fetch",
        "description": "Run git fetch --prune for one configured remote. Requires approval and may contact the remote.",
        "input_schema": {
            "type": "object",
            "properties": {
                "remote": {
                    "type": "string",
                    "description": "Remote name to fetch, such as origin. If omitted, the single configured remote is selected.",
                },
            },
            "additionalProperties": False,
        },
    },
{
        "name": "check_git_pull",
        "description": "Validate whether the current branch can be updated from its upstream with git pull --ff-only without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
{
        "name": "git_pull",
        "description": "Update the current branch from its configured upstream using git pull --ff-only. Requires approval, a clean worktree, and no divergent local commits.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
{
        "name": "check_git_push",
        "description": "Validate whether the current branch can be pushed to its configured upstream without changing local or remote refs.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
{
        "name": "git_push",
        "description": "Push the current branch to its configured upstream. Requires approval, a clean worktree, ahead commits, and no cached behind state. Does not force push.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
{
        "name": "check_git_switch",
        "description": "Validate switching to an existing local branch or creating a new local branch without changing HEAD.",
        "input_schema": {
            "type": "object",
            "properties": {
                "branch": {"type": "string", "description": "Local branch name to switch to or create."},
                "create": {
                    "type": "boolean",
                    "description": "Create the branch with git switch -c when true. Defaults to false.",
                },
            },
            "required": ["branch"],
            "additionalProperties": False,
        },
    },
{
        "name": "git_switch",
        "description": "Switch to an existing local branch, or create and switch to a new local branch. Requires approval and a clean worktree.",
        "input_schema": {
            "type": "object",
            "properties": {
                "branch": {"type": "string", "description": "Local branch name to switch to or create."},
                "create": {
                    "type": "boolean",
                    "description": "Create the branch with git switch -c when true. Defaults to false.",
                },
            },
            "required": ["branch"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_git_stage",
        "description": "Validate staging one or more project-relative paths without changing the git index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Project-relative paths to stage, such as src/app.py or tests.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
{
        "name": "git_stage",
        "description": "Stage one or more project-relative paths in the git index. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Project-relative paths to stage, such as src/app.py or tests.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_git_unstage",
        "description": "Validate unstaging one or more project-relative paths without changing the git index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Project-relative paths to unstage, such as src/app.py or tests.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
{
        "name": "git_unstage",
        "description": "Unstage one or more project-relative paths from the git index. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Project-relative paths to unstage, such as src/app.py or tests.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_git_restore",
        "description": "Preview discarding unstaged changes for tracked project-relative paths without changing files or the git index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Tracked project-relative paths whose unstaged changes would be restored from HEAD.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
{
        "name": "git_restore",
        "description": "Discard unstaged changes for tracked project-relative paths with git restore. Requires approval. Does not delete untracked files or change the git index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Tracked project-relative paths whose unstaged changes should be restored from HEAD.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
{
        "name": "git_stashes",
        "description": "List recent git stash entries without changing the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_entries": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum stash entry count to return. Defaults to 20.",
                },
            },
            "additionalProperties": False,
        },
    },
{
        "name": "check_git_stash",
        "description": "Preview saving current non-runtime changes to git stash without changing the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Optional stash message. Defaults to 'vibeagent stash'."},
                "include_untracked": {
                    "type": "boolean",
                    "description": "Also stash non-runtime untracked files. Defaults to false.",
                },
            },
            "additionalProperties": False,
        },
    },
{
        "name": "git_stash",
        "description": "Save current non-runtime changes to git stash. Requires approval. Excludes .vibeagent runtime files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Optional stash message. Defaults to 'vibeagent stash'."},
                "include_untracked": {
                    "type": "boolean",
                    "description": "Also stash non-runtime untracked files. Defaults to false.",
                },
            },
            "additionalProperties": False,
        },
    },
{
        "name": "check_git_stash_apply",
        "description": "Preview applying one stash entry to a clean worktree without changing files or dropping the stash.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stash_ref": {"type": "string", "description": "Stash reference such as stash@{0}."},
            },
            "required": ["stash_ref"],
            "additionalProperties": False,
        },
    },
{
        "name": "git_stash_apply",
        "description": "Apply one stash entry to a clean worktree. Requires approval. Does not drop the stash.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stash_ref": {"type": "string", "description": "Stash reference such as stash@{0}."},
            },
            "required": ["stash_ref"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_git_stash_drop",
        "description": "Preview dropping one stash entry without changing the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stash_ref": {"type": "string", "description": "Stash reference such as stash@{0}."},
            },
            "required": ["stash_ref"],
            "additionalProperties": False,
        },
    },
{
        "name": "git_stash_drop",
        "description": "Drop one stash entry after approval. This permanently removes the stash entry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stash_ref": {"type": "string", "description": "Stash reference such as stash@{0}."},
            },
            "required": ["stash_ref"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_git_commit",
        "description": "Validate that currently staged changes can be committed with the provided message without creating a commit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message to validate.",
                },
            },
            "required": ["message"],
            "additionalProperties": False,
        },
    },
{
        "name": "git_commit",
        "description": "Commit currently staged changes with a message. Uses --no-verify and does not run git hooks. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message, up to 500 characters.",
                },
            },
            "required": ["message"],
            "additionalProperties": False,
        },
    },
{
        "name": "review_changes",
        "description": "Run a read-only pre-final review: structured changed files, git diff whitespace checks, and Python syntax checks for changed Python files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum changed file and Python file count to report. Defaults to 200.",
                },
            },
            "additionalProperties": False,
        },
    },
{
        "name": "final_review",
        "description": "Run a read-only final handoff review that summarizes blocking issues, warnings, changed files, and suggested verification commands before finishing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum changed file count to report. Defaults to 200.",
                },
                "max_checks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum suggested verification command count to report. Defaults to 10.",
                },
            },
            "additionalProperties": False,
        },
    },
{
        "name": "suggest_checks",
        "description": "Suggest relevant test, build, lint, and syntax-check commands from project metadata and current changed files without running them, including whether each command's main executable is available on PATH.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum suggested command count to return. Defaults to 20.",
                },
            },
            "additionalProperties": False,
        },
    },
{
        "name": "check_suggested_checks",
        "description": "Preflight the project's suggested test, build, lint, and syntax-check commands without running them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum suggested command count to preflight. Defaults to 10.",
                },
            },
            "additionalProperties": False,
        },
    },
{
        "name": "run_suggested_checks",
        "description": "Run the project's available suggested test, build, lint, and syntax-check commands after approval. Stops at the first failure by default.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum suggested command count to run. Defaults to 10.",
                },
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 600000,
                    "description": "Optional timeout in milliseconds per command. Defaults to the agent command timeout.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Optional stdout/stderr character cap per command. Defaults to 12000.",
                },
                "stop_on_failure": {
                    "type": "boolean",
                    "description": "Stop after the first failing command. Defaults to true.",
                },
                "extract_output_contexts": {
                    "type": "boolean",
                    "description": "When true, extract file:line references from stdout/stderr and include source context for each reference. Defaults to false.",
                },
                "extract_output_diagnostics": {
                    "type": "boolean",
                    "description": "When true, summarize error/warning/failure diagnostic lines from stdout/stderr and include source contexts for referenced project files. Defaults to false.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 500,
                    "description": "Lines before and after each extracted reference when extract_output_contexts or extract_output_diagnostics is true. Defaults to 5.",
                },
                "max_diagnostics": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum diagnostic lines to include when extract_output_diagnostics is true. Defaults to 50.",
                },
                "max_contexts": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum extracted contexts to include when extract_output_contexts or extract_output_diagnostics is true. Defaults to 20.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per extracted file context when extract_output_contexts or extract_output_diagnostics is true. Defaults to 20000.",
                },
            },
            "additionalProperties": False,
        },
    },
]
