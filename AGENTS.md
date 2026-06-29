# AGENTS.md

`dotbrain` — one tool that wires **project Brainspaces** and **skills** into whatever coding
agent you use (Claude Code, Codex). Engineering-centered.

## What this is

dotbrain separates the durable context an agent needs from the code it works on. For each project
you keep a **Brainspace** that holds the project's **Brain** (`.brain/` — domain vocabulary,
decisions, operating rules), an **execution store** (`.beads/`), and **agent workspaces**
(`.claude/`, `.codex/`). Your code repo gets gitignored symlinks into that Brainspace, so agents
pick up project memory and a live issue tracker without that material living in the code repo.

Skills are agent-owned, not project-owned: a Brain only *configures* the skills it uses. The
bundled `src/dotbrain/resources/skills/brain/` set is dotbrain's own operating manual (wiring, brain authoring, execution).

## Public / private boundary

This repository is the **tool**, and it is public. A user's **Brainspaces and Brains are private**
and live in a separate data root (by convention `~/dotbrain`) that this tool operates on. The tool
never contains anyone's project data. dotbrain's own design record (ADRs) lives in its private Brain;
this repo ships only the *derived* [docs/architecture.md](docs/architecture.md).

If you are an agent working in this repo, treat it as a normal public codebase: do not assume a
`.brain/` is present (it is local, gitignored wiring on the maintainer's machine only).

## Layout

- `src/dotbrain/` — the Python CLI (`wire`, `unwire`, `bootstrap`, `refresh`, `skills link`, …).
- `src/dotbrain/resources/` — packaged runtime assets:
  - `skills/brain/` — bundled product skills (the system's own operating manual).
  - `templates/brain/` — Brain scaffold seeded into a new Brainspace.
  - `scripts/` — hook implementations invoked through `dotbrain hook ...`.
  - `config.yaml` — shipped example config; seeded into data root by bootstrap.
- `tests/` — the CLI test suite (`uv run pytest`).
- `docs/architecture.md` — the design narrative.

## Quickstart

```bash
./install.sh        # installs uv, Beads (bd), and the dotbrain CLI
dotbrain bootstrap        # install agent hooks and link global skills
dotbrain wire <repo>      # connect a code repo to a Brainspace under your data root
```

See [README.md](README.md) for more, and [docs/architecture.md](docs/architecture.md) for the model.

## Development

```bash
uv sync                                  # create the venv and install deps
uv run pytest                            # run the full suite
uv run pytest tests/test_wiring.py       # one file
uv run pytest -k worktree                # match by name
uv run pytest tests/test_workflows.py::test_unwire_all_disconnects_every_repo  # one test
uv tool install --editable --force .     # install the `dotbrain` CLI from this checkout
```

The package entrypoint is `dotbrain.cli:app` (Typer); `python -m dotbrain` is not wired.
Tests are `tmp_path`-based — they never touch a real `$HOME` or the live data root. There is no
configured linter; the stray `# noqa: A002` markers are advisory only.

## Codebase architecture

For the product model (Brainspaces, the Brain/execution split, the public/private boundary) read
[docs/architecture.md](docs/architecture.md). For the *code*, the shape is a strict dependency
layering under `src/dotbrain/`:

- **`paths.py`** — the pure foundation. Encodes the wiring contracts (the four `BRAINSPACE_LINKS`,
  exclude entries, the adopter pointer, data-root resolution) as side-effect-free functions. No
  filesystem mutation here; everything else builds on it and depends *into* it, never the reverse.
- **Concept modules**, each owning one concept and depending only on `paths` (and sometimes
  `config`): `adopter_repos` (repo-facing symlinks, `.git/info/exclude`, AGENTS.md pointer),
  `brainspaces` (Brain + agent-workspace seeding, offboarding), `beads` (the `bd` tracker),
  `skills` and `subagents` (curated symlink linking), `bootstrap` (machine-global setup),
  `migrate` (embedded→server beads, composing `beads` helpers), `doctor` (read-only health).
- **`workflows.py`** — cross-concept orchestration; the bodies behind `wire`, `wire --all`,
  `unwire`, `refresh`. It stitches the concept modules together.
- **`cli.py`** — a thin Typer parsing/rendering layer over `workflows` and the modules. Keep logic
  out of here.
- **`resource_loader.py`** — the only accessor for packaged `dotbrain.resources` (skills,
  templates, scripts) via `importlib.resources`.

Two patterns to know before changing anything:

- **Subprocess seam.** Modules that shell out to `bd`/`git` take an injected `run` callable
  (`Runner`, same shape as `subprocess.run`). Tests pass a fake that records argv instead of
  executing. Preserve this seam — assertions are on the recorded commands.
- **Checkout vs. data root.** The *checkout* (this repo) is the tool source. The *data root*
  (`$DOTBRAIN_HOME`, by convention `~/dotbrain`) holds `brainspaces/`, `skills/`, and the seeded
  `config.yaml`; it is resolved by `paths.resolve_dotbrain_home()`. Config splits into a global
  `config.yaml` (infra defaults like `beads.server`) and a per-project `brainspaces/<name>/project.yaml`
  (beads mode, skill and subagent selection). Don't conflate the two roots.

## Conventions

- `AGENTS.md` is canonical; `CLAUDE.md` is a symlink to it.
- Prefer the nearest local context file in any directory tree.
- Symlinks whose targets are outside the containing git repo are local wiring: gitignore them,
  never track them.
