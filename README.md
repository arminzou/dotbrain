# dotbrain

An agent-native control plane. dotbrain keeps each project's durable context — domain
knowledge, decisions, and a live issue tracker — in a **control root** outside the code repo,
and wires it into your coding agent (Claude Code, Codex) through gitignored symlinks. Your code
repo stays clean; your agent gets project memory and execution state for free.

## Why

Coding agents are only as good as the context they start with. dotbrain gives every project a
**Brain** (vocabulary, architecture decisions, operating rules) and an **execution store**, links
them into the agent's session automatically, and keeps that material private even when the code
repo is public.

## Install

```bash
git clone https://github.com/arminzou/dotbrain.git
cd dotbrain
./install.sh        # installs uv, Beads (bd), and the dotbrain CLI
dotbrain bootstrap        # install agent hooks and link global skills
```

## Use

```bash
dotbrain wire <repo>      # connect a code repo to a control root
dotbrain refresh          # repair wiring, load execution state, link project skills
dotbrain unwire <repo>    # disconnect a repo from its control root
```


## Develop

The CLI is a [uv](https://docs.astral.sh/uv/)-managed Python package.

```bash
uv sync                 # provision the env
uv run dotbrain --help  # inspect the command tree
uv run pytest           # run the test suite
```

## Learn more

- [AGENTS.md](AGENTS.md) — the system model and agent entrypoint.
- [docs/architecture.md](docs/architecture.md) — the design narrative: control roots, the
  Brain/execution split, skills, and the public/private boundary.
