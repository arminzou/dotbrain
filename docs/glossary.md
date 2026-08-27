# Glossary

## Core Terms

### dotbrain

The tool itself. dotbrain wires a private Brainspace and skill/runtime setup into a code repo
without moving that private state into the repo.

### Brainspace

The private per-project home under `~/dotbrain/brainspaces/<name>/`. A Brainspace contains the
project's Brain plus agent/runtime adapters such as `.beads`, `.claude`, and `.codex`.

### Brainspace links

The gitignored links placed in a repo that point back to the private Brainspace. Typical links are
`.brain` and `.beads`; `.claude` and `.codex` are project-owned directories with individually
ignored dotbrain resources.

### Brain

The durable knowledge layer for a project. The Brain holds project context, decisions, and
agent-facing conventions. In dotbrain terms, the Brain is narrower than the full Brainspace.

### Brain-only project

A project that keeps Brain context without using an execution store in practice, or without wiring a
normal code repo as its main surface. The Brain still exists; the surrounding workflow is lighter.

### config.yaml

The global dotbrain config file, usually at `~/dotbrain/config.yaml`. It holds machine-wide
defaults such as shared beads server settings.

### project.yaml

The per-project config file at `~/dotbrain/brainspaces/<name>/.brain/project.yaml`. It declares project-level
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

The runtime-specific workspace directory in a repo, such as `.claude/` or `.codex/`. dotbrain links
only its selected resources inside it.

### public tracker

The outward-facing issue system used for public intake and contributor collaboration, such as
GitHub Issues. Existing public issues may be promoted into the private execution graph with a
provenance link. Private designs, epics, and work items are never projected outward as public
tracking issues; a PR can provide a public review surface without one.

### worktree

A git worktree that shares the same repo history but has its own working directory. In dotbrain,
`wire-brain`'s worktree repair branch can link its `.brain` and `.beads` back to the main checkout.

### bootstrap

The machine-level setup step run by `dotbrain bootstrap`. It seeds global config and links global
skills.

### skill

A reusable agent capability with its own instructions and, sometimes, reference material.

### brain-coupled skill

A skill that operates directly on a project's Brain or execution state. dotbrain ships a required
core of these skills as part of its operating model.

### adopter repo

A normal code repo that dotbrain wires to a private Brainspace. The adopter repo stays focused on
the code; the Brain and execution state live outside it.

### derive

To create a public-facing explanation or artifact from private source material without exposing the
private source directly. dotbrain uses this boundary to keep Brains private while still publishing
docs or tooling publicly.

## Excluded Terms

This glossary intentionally leaves out lower-level implementation jargon and private internal
phrasing. It is meant to explain the public conceptual model, not every CLI mutation path or
historical term.
