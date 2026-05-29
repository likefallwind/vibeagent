# VibeAgent

VibeAgent v1 is a minimal command-line ReAct coding agent. It asks MiniMax for one JSON action at a time, executes that action inside a per-run workspace under `.vibeagent/runs/`, and feeds command output back to the model until the task finishes or the iteration limit is reached.

## Setup

```sh
npm install
npm run build
```

Set a MiniMax API key:

```sh
export MINIMAX_API_KEY="..."
```

`minimax_api` is also accepted as a fallback environment variable.

## Usage

```sh
npm run dev
```

or after building:

```sh
vibeagent
```

Example task:

```text
写一个 JS 程序计算 1 到 100 的和并运行。
```

## v1 Boundaries

- Files are written only inside `.vibeagent/runs/<run-id>/`.
- Commands run only from that run directory.
- Commands time out after 30 seconds by default.
- V1 is a local development prototype, not a security sandbox. It does not try to block every dangerous shell command.
