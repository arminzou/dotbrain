# Glossary

## Core Terms

### dotbrain

The tool itself. dotbrain wires a private control root and skill/runtime setup into a code repo
without moving that private state into the repo.

### control root

The private per-project home under `~/dotbrain/projects/<name>/`. A control root contains the
project's Brain plus agent/runtime adapters such as `.beads`, `.claude`, and `.codex`.

### control-root links

The gitignored links placed in a repo or worktree that point back to the private control root.
Typical links are `.brain`, `.beads`, `.claude`, and `.codex`.

### Brain

The durable knowledge layer for a project. The Brain holds project context, decisions, and
agent-facing conventions. In dotbrain terms, the Brain is narrower than the full control root.

### Brain-only project

A project that keeps Brain context without using an execution store in practice, or without wiring a
normal code repo as its main surface. The Brain still exists; the surrounding workflow is lighter.

### config.yaml

The global dotbrain config file, usually at `~/dotbrain/config.yaml`. It holds machine-wide
defaults such as shared beads server settings.

### project.yaml

The per-project config file at `~/dotbrain/projects/<name>/project.yaml`. It declares project-level
settings such as execution engine choice, public tracker choice, seeded agent workspaces, beads
deviations, and extra skills.

### execution engine

The backend that holds the private execution graph for a project. Today that is beads, but the term
describes the role rather than a specific implementation.

### execution store

The live state managed by the execution engine. In practical terms, this is where open work,
dependencies, readiness, and closure state live.

### agent runtime

The coding agent environment dotbrain wires into, such as Claude Code or Codex.

### agent workspace

The runtime-specific workspace config dotbrain links into a repo or worktree, such as `.claude/` or
`.codex/`.

### public tracker

The outward-facing issue system used for public intake, such as GitHub Issues. It is linked to the
private execution graph, not treated as the source of truth for execution.

### worktree

A git worktree that shares the same repo history but has its own working directory. In dotbrain, a
worktree can be wired to the same control root as the main checkout.

### bootstrap

The machine-level setup step run by `dotbrain bootstrap`. It seeds global config, installs global
hooks, and links global skills.

### skill

A reusable agent capability with its own instructions and, sometimes, reference material.

### brain-coupled skill

A skill that operates directly on a project's Brain or execution state. dotbrain ships a required
core of these skills as part of its operating model.

### adopter repo

A normal code repo that dotbrain wires to a private control root. The adopter repo stays focused on
the code; the Brain and execution state live outside it.

### derive

To create a public-facing explanation or artifact from private source material without exposing the
private source directly. dotbrain uses this boundary to keep Brains private while still publishing
docs or tooling publicly.

## Two-Agent Terms

For the coordination terms below, see
[two-agent-protocol.md](/home/armin/repos/projects/dotbrain/docs/two-agent-protocol.md):

- `main-agent`
- `worker`
- `slice`
- `landing`

## Excluded Terms

This glossary intentionally leaves out lower-level implementation jargon and private internal
phrasing. It is meant to explain the public conceptual model, not every CLI mutation path or
historical term.
