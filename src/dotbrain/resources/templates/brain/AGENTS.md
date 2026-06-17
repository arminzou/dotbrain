# AGENTS.md

Private agent context for this project. The repo-root `AGENTS.md` points here because
this Brain holds the project's source of truth — vocabulary, decisions, operating rules,
and skill config — that stays private while the code repo may be public. Execution lives
in beads (`bd`), not in here.

`DOTBRAIN.md` carries the shared operating rules (wiring, conventions, public/private
boundary) and is rehydrated by `dotbrain bootstrap`.

## Read order

1. `DOTBRAIN.md` — shared operating rules, wiring, and conventions
2. `bd ready` / `bd list` from the repo root — execution state (issues live in beads)
3. `CONTEXT.md` — domain vocabulary
4. `adr/` — decisions, one per file
5. `agents/` — project-specific skill config and conventions; read when a skill directs you to

## Project

(Add project-specific rules and conventions here.)
