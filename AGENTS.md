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

## Conventions

- `AGENTS.md` is canonical; `CLAUDE.md` is a symlink to it.
- Prefer the nearest local context file in any directory tree.
- Symlinks whose targets are outside the containing git repo are local wiring: gitignore them,
  never track them.
