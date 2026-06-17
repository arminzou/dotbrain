# Agent Context

This file is the root-level agent context for `<workspace-root>`.

## Scope

Use this file only when working directly under this root or when a subdirectory does not provide its own `AGENTS.md` or `CLAUDE.md`.

If a project has a nearer local context file, that local file overrides this one.

## Purpose of the Root Context

Keep this root file high-level.

It should give agents enough shared context to navigate this workspace safely:
- top-level directory layout
- organization conventions
- important locations
- cross-cutting rules

Do not put detailed project-specific operating instructions here when they belong in a nearer file.

## Context File Convention

- `AGENTS.md` is the canonical agent context file.
- `CLAUDE.md` should be a symlink to `AGENTS.md` when both names are needed.
- Prefer the nearest context file in the current directory tree.
- Keep root guidance generic and reusable.

## Top-Level Directory Layout

| Path | Purpose |
|------|---------|
| `<path>` | `<purpose>` |

## Workspace Organization Conventions

- Put substantial code projects under `<path>` unless there is a clear reason not to.
- Keep project-specific instructions with the project itself.
- Add a local `AGENTS.md` once a repo becomes non-trivial.

## Important Cross-Cutting Notes

- `<cross-cutting caution>`
- `<shared convention>`
