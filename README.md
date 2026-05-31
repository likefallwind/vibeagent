# VibeAgent

VibeAgent v1 is a minimal command-line ReAct coding agent written in Python. It asks MiniMax for one JSON action at a time, executes that action inside a per-run workspace under `.vibeagent/runs/`, and feeds command output back to the model until the task finishes or the iteration limit is reached.

## Setup

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

There are no required third-party runtime dependencies.

Set a MiniMax API key:

```sh
export MINIMAX_API_KEY="..."
```

The client reads the API key from environment variables automatically.
`MINIMAX_API` and `minimax_api` are also accepted as fallback environment variables.
If you paste a value like `Bearer sk-...`, VibeAgent strips the `Bearer` prefix automatically.
By default VibeAgent calls MiniMax's Anthropic-compatible endpoint at
`https://api.minimaxi.com/anthropic/v1/messages`.

## Usage

```sh
python -m vibeagent
```

or through the npm compatibility scripts:

```sh
npm run dev
```

Use `/help` to list local commands, `/model` to inspect the configured MiniMax model and API key source, and `/exit` to leave the interactive prompt. For generated code, the agent now prefers Python scripts unless the user asks for another language.

Example task:

```text
写一个 Python 程序计算 1 到 100 的和并运行。
```

## Architecture

VibeAgent is intentionally small. The runtime is a loop that asks the model for
one JSON action, executes that action in an isolated run directory, then sends
the observation back to the model on the next iteration.

High-level flow:

```text
CLI input
  -> run_agent()
  -> build_messages()
  -> MiniMaxClient.complete()
  -> parse_model_action()
  -> execute_action()
  -> observation appended to next prompt
```

Core modules:

- `vibeagent/cli.py`: interactive command-line entry point. It handles local
  commands such as `/help`, `/model`, and `/exit`, then delegates programming
  tasks to the agent loop.
- `vibeagent/agent.py`: orchestrates the ReAct loop. It creates a run
  workspace, builds model prompts, parses model actions, executes them, and
  stops on a `finish` action or the iteration limit.
- `vibeagent/prompts.py`: owns the system prompt and user message construction.
  Each prompt includes the original task, current run directory, workspace file
  snapshot, and previous observations.
- `vibeagent/minimax.py`: MiniMax API client. It reads API configuration from
  environment variables, calls the Anthropic-compatible MiniMax endpoint, and
  normalizes supported response shapes into plain text.
- `vibeagent/actions.py`: parses model JSON into typed actions and executes
  them. Supported actions are `write_file`, `run_command`, and `finish`.
- `vibeagent/workspace.py`: creates `.vibeagent/runs/<run-id>/`, resolves
  relative file paths, rejects path escapes, writes generated files, and builds
  workspace snapshots for prompts.
- `vibeagent/types.py`: shared dataclasses and protocols for chat messages,
  actions, command results, observations, and agent status.

The model contract is deliberately narrow: every model response should contain
a JSON object with a `thought` string and one `action`. The parser accepts the
first complete JSON object if the model emits extra text or multiple JSON
objects, but the agent still executes only one action per iteration.

## v1 Boundaries

- Files are written only inside `.vibeagent/runs/<run-id>/`.
- Commands run only from that run directory.
- Commands time out after 30 seconds by default.
- V1 is a local development prototype, not a security sandbox. It does not try to block every dangerous shell command.

## Development

```sh
python -m unittest discover -s tests
npm test
```
