# Repository Guidelines

## Project Structure & Module Organization

VibeAgent is a small Python 3.11+ CLI package. Core source lives in `vibeagent/`: `cli.py` handles the interactive command loop, `agent.py` runs the ReAct workflow, `actions.py` executes tool actions, `workspace.py` enforces project boundaries, and provider adapters live in `minimax.py`, `openai_compat.py`, and `providers.py`. Tests are in `tests/test_*.py` and mirror the module names. `bin/vibeagent` and `package.json` provide npm-compatible entry points. Treat `.vibeagent/`, `dist/`, `*.egg-info/`, `__pycache__/`, and `.pytest_cache/` as generated or local runtime artifacts.

## Build, Test, and Development Commands

- `python3 -m venv .venv && . .venv/bin/activate`: create and enter a local virtual environment.
- `python -m pip install -e .`: install the package in editable mode.
- `python -m vibeagent`: run the CLI directly.
- `npm run dev` or `npm start`: compatibility wrappers for `python3 -m vibeagent`.
- `npm test` or `python3 -m unittest discover -s tests`: run the full unit test suite.
- `npm run build`: compile-check the package with `python3 -m compileall -q vibeagent`.

## Coding Style & Naming Conventions

Use Python with 4-space indentation, type hints, dataclasses where they fit, and explicit imports from local modules. Keep the provider-neutral types in `types.py` stable unless the adapter contract changes. Name modules in lowercase snake_case, tests as `test_<module>.py`, test classes as `<Feature>Tests`, and test methods as `test_<behavior>`.

## Testing Guidelines

The suite uses `unittest`; keep new tests deterministic and avoid real provider calls unless explicitly validating integration behavior. Prefer temporary directories for workspace tests, as existing tests do with `tempfile.TemporaryDirectory`. When packaging behavior changes, validate from outside the repo root, for example from `runtest/`, so editable installs do not pass only because of the current working directory.

## Commit & Pull Request Guidelines

Recent history uses short subjects such as `tool call`, `修复`, and `Add architecture note and module-level code comments`; there is no strict Conventional Commit pattern. Keep commit subjects concise and describe the changed behavior. PRs should include the problem, the implementation summary, commands run, linked issues if any, and terminal or CLI screenshots only when user-visible behavior changes.

## Security & Configuration Tips

Do not commit API keys. MiniMax is the default provider and reads `MINIMAX_API_KEY`, then `MINIMAX_API`, then `minimax_api`. OpenAI-compatible providers use `VIBEAGENT_PROVIDER`, `OPENAI_COMPAT_API_KEY`, `OPENAI_COMPAT_BASE_URL`, and `OPENAI_COMPAT_MODEL`. Preserve workspace safety rules: model file actions must stay inside the active project and must not mutate `.git/` or `.vibeagent/`. File writes, file edits, and command runs require approval before execution; library calls without an approval handler deny those actions by default. High-risk commands such as `sudo` and `rm -rf /` remain blocked even when command execution is approved.
