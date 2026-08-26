# Agent Context

This file is the repo-level agent context for `<project-path>`.

## Scope

Use this file for work inside this project tree. It overrides any broader root-level context.

`AGENTS.md` is canonical. `CLAUDE.md` should remain a symlink to `AGENTS.md`.

## Private Context

This repo may be wired to private dotbrain context at `.brain/AGENTS.md`.

If `.brain/AGENTS.md` exists locally, read it before substantial agent work for private project
operations, execution tracking, roadmap, ADRs, and domain vocabulary.

If `.brain/AGENTS.md` does not exist, continue from this public context. Do not treat the missing
private context as an error, and do not create public replacement files for private dotbrain state.

## Project Purpose

- `<what this project is>`
- `<what this project is not>`

## Important Paths

| Path | Purpose |
|------|---------|
| `<path>` | `<purpose>` |

## Working Conventions

- `<code organization convention>`
- `<where docs live>`
- `<naming or layering rule>`

## Commands and Verification

- Build: `<command>`
- Test: `<command>`
- Run: `<command>`

## Important Notes / Traps

- `<non-obvious hazard>`
- `<dependency or environment quirk>`
