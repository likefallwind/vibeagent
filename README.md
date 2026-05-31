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
