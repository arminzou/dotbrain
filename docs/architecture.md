# Architecture

dotbrain gives every project a durable context store that lives outside the code repo and wires it
into your coding agent automatically. This document explains how it is put together and why.

## The problem

A coding agent starts every session cold. The context that makes it effective — a project's
vocabulary, its architectural decisions, the rationale behind past choices, and what work is in
flight — usually lives in someone's head or scattered across docs. Putting that material in the code
repo is awkward: much of it is private, it is not really *code*, and it drifts.

dotbrain's premise: give every project a structured context store that lives *outside* the code
repo, and wire it into the agent so each session starts warm.

## Control roots

The unit of organization is a **control root** — one directory per project that holds everything an
agent needs that is not the code itself:

- `.brain/` — the project's knowledge (see below)
- `.beads/` — the execution store (issues, dependencies, plans)
- `.claude/`, `.codex/` — agent workspaces (settings, worktrees)

Control roots live together in a single repository. A code repo connects to its control root through
**gitignored symlinks** at the repo root (`.brain`, `.beads`, `.claude`, `.codex`). Because the
symlink targets are outside the code repo, they are never tracked there — they are local machine
wiring. The code repo stays clean and the context stays private, while the agent sees both as one
tree.

## The Brain

A Brain has four elements, each with a single clear purpose:

- **`CONTEXT.md`** — the project's domain vocabulary. Names for concepts that issues, plans, and code
  use consistently, so language does not drift into synonyms.
- **`adr/`** — Architecture Decision Records, one file per decision. Each captures a choice that is
  hard to reverse, surprising without context, and the result of a real trade-off.
- **`agents/`** — skill configuration: which skills a project uses and how they are set up.
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

Connecting a repo is one command: `dotbrain wire` creates or repairs the control root, writes the
four symlinks, and records the ignore rules that keep them out of the code repo. A one-time
`dotbrain bootstrap` installs the agent hooks for the machine.

At the start of every agent session, a hook injects the shared operating rules and the project's own
Brain context into the session, so the agent begins already knowing the project's conventions without
anyone pasting them in. Worktrees reach the same Brain through the same symlinks — never a
per-worktree copy.

## Public / private boundary

The decision that shapes everything: **the tool is public; your data is private.** This repository is
the tool — CLI, bundled skills, templates, scripts. Your control roots and Brains live in a separate,
private data root that the installed tool operates on. The tool never contains project data, and a
Brain is never mirrored into a public code repo. When something genuinely needs to be public, you
*derive* a fresh, audience-specific document instead of exposing the private source.

That boundary is what lets you run dotbrain as an open-source tool while keeping it, unchanged, for
entirely private work.
