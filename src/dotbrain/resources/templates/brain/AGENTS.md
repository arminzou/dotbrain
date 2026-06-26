# AGENTS.md

Private agent context for this project. The repo-root `AGENTS.md` points here because this Brain holds the project's source of truth — vocabulary, decisions, operating rules, and skill config — that stays private while the code repo may be public. Execution lives in beads (`bd`), not in here.

`DOTBRAIN.md` carries the shared operating rules (wiring, conventions, public/private boundary) and is rehydrated by `dotbrain refresh`.

## Project

Cross-cutting rules with no structured home: build and test commands, project-wide constraints, gotchas, and project tracker conventions (linking rules, ADR-pairing policy, priority deviations) read by `operate-execution` and `triage-public` — absent or empty means pure defaults. Vocabulary goes in CONTEXT.md, decisions in adr/, skill selection in project.yaml.
