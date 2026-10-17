# Agent Handbook

## Before starting

Read the guidance relevant to your task. Prefer nearer `AGENTS.md` instructions
when working within a directory.

- Before making or reviewing a change, read [RULES.md](RULES.md).
- For product usage and setup, read [README.md](README.md).
- Before changing design boundaries, read [docs/architecture.md](docs/architecture.md).

## CLI implementation

- For command behavior, start with `src/dotbrain/cli.py` for parsing,
  `workflows.py` for orchestration, then the relevant concept module.
- For wiring and path contracts, read [docs/wiring.md](docs/wiring.md) and
  inspect `src/dotbrain/paths.py`.
- For packaged resources, inspect `src/dotbrain/resources/` and its accessor,
  `src/dotbrain/resource_loader.py`.
- For configuration changes, read [docs/configuration.md](docs/configuration.md).

## Agent workflows and runtime integration

- For workflow or skill instructions, read
  [plugin/skills/README.md](plugin/skills/README.md), then the relevant definitions
  under `plugin/`.
- For resource delivery and runtime discovery, read the
  [runtime delivery guidance](docs/session-context.md#subagents), then inspect
  `src/dotbrain/skills.py`, `src/dotbrain/subagents.py`, and their corresponding tests.
- For session-start behavior, inspect `plugin/hooks/`, `src/dotbrain/hooks.py`,
  and `tests/test_hooks.py`.

## Documentation

Before editing public documentation, read [docs/AGENTS.md](docs/AGENTS.md).
Check the corresponding English and Chinese pages for affected guidance.

## Verification

Select relevant checks under `tests/`:

- Install dependencies: `uv sync`
- Run affected tests: `uv run pytest tests/<file>.py`
- Run the suite: `uv run pytest`
- Install the CLI from this checkout: `uv tool install --editable --force .`

Resource files being present does not prove the runtime loads them. For runtime
loading claims, verify discovery or invocation in the affected runtime.
