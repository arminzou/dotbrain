# Architecture

This document explains dotbrain's design: Brainspaces, the Brain and execution split, skills, and
the public/private boundary. For the problem dotbrain solves and how to get started, see the
[README](../README.md).

## Brainspaces

The unit of organization is a **Brainspace** — one directory per project that holds everything an
agent needs that is not the code itself:

- `.brain/` — the project's knowledge (see below)
- `.beads/` — the execution store (issues, dependencies, plans)

Brainspaces live together in a single repository. A code repo connects to its Brainspace through
the gitignored `.brain` and `.beads` symlinks. Its `.claude` and `.codex` agent workspaces are real
directories; dotbrain contributes individually ignored skill and subagent links without claiming
project-owned files. The code repo stays clean and the context stays private, while the agent sees
both as one tree.

## The Brain

A Brain has five elements, each with a single clear purpose:

- **`CONTEXT.md`** — the project's domain vocabulary. Names for concepts that issues, plans, and code
  use consistently, so language does not drift into synonyms.
- **`adr/`** — Architecture Decision Records, one file per decision. Each captures a choice that is
  hard to reverse, surprising without context, and the result of a real trade-off.
- **`designs/`** — design docs, one initiative per file. While a design is active, it is the
  living design authority for the initiative: current design, known unknowns, and deviations live
  there. Authored by `to-design`, decomposed into bead epics by `to-issues`. Beads remain the
  execution/status source. Once shipped, abandoned, or superseded, the design doc freezes as a
  point-in-time record.
- **`AGENTS.md`** — per-project agent operating conventions: linking rules, ADR policy, priority.
- **`project.yaml`** — per-project runtime selection plus skill and subagent selection.
- **`docs/`** — derived runbooks and reference material. Never authoritative; the elements above win.

Brain writes are version-controlled, so every change is reviewable and revertable. Each element has
a single writer rather than every agent editing everything, which keeps the knowledge coherent.

## Execution lives in the tracker

Plans and tasks do not live as markdown checklists that rot. They live in an **execution store** — by
default [Beads](https://github.com/gastownhall/beads) (`bd`), a dependency-aware issue tracker.
Multi-step work is modeled as issues with blocking relationships, so "what is ready to work on" is a
query, not a document. The execution store is treated as machine-local runtime state, hydrated from
configuration — which lets the same backend run locally (embedded) or as a shared server across
machines, configured per project. The tracker is pluggable behind a small contract, so a project can
swap the backend without changing how agents work.

## Skills

Skills are reusable agent capabilities, owned by the tool rather than any one project. dotbrain
manages a curated set: a small baseline that is always present, plus per-project and operator-chosen
additions. Linking is reconciled idempotently — the tool only ever creates or prunes the symlinks it
owns, and never deletes a real file or a link it did not create. That is what lets the bundled
product skills coexist safely with an operator's own private skills on the same machine.

## Wiring and session start

Connecting a repo is one command: `dotbrain wire` creates or repairs the Brainspace, writes its two
links, materializes the agent workspaces, and records per-link ignore rules. A one-time
`dotbrain bootstrap` installs the agent hooks for the machine and links global skills and
subagents.

At the start of every agent session, a hook injects the shared operating rules and the project's own
Brain context into the session, so the agent begins already knowing the project's conventions without
anyone pasting them in. Project-selected skills and vendor-native subagents are linked into the
matching workspaces from the same Brainspace declarations. Worktrees reach the same Brain through
their own links — never a
per-worktree copy.

## Public / private boundary

The decision that shapes everything: **the tool is public; your data is private.** This repository is
the tool — CLI, bundled skills, templates, scripts. Your Brainspaces and Brains live in a separate,
private data root that the installed tool operates on. The tool never contains project data, and a
Brain is never mirrored into a public code repo. When something genuinely needs to be public, you
*derive* a fresh, audience-specific document instead of exposing the private source.

That boundary is what lets you run dotbrain as an open-source tool while keeping it, unchanged, for
entirely private work.
