# DOTBRAIN.md

Shared operating rules for all dotbrain brains. Owned by dotbrain; rehydrated by
`dotbrain refresh`. Do not edit per project — changes to the packaged dotbrain
Brain template propagate to every brain.

## Wiring

- This Brain lives in the private dotbrain home at
  `~/dotbrain/brainspaces/<name>/.brain`, not in the code repo.
- Repo-root `.brain`, `.beads`, `.claude`, and `.codex` are gitignored symlinks into that
  Brainspace. They are local machine wiring: never commit them to the code repo.
- Brain changes are committed in `~/dotbrain`. The code repo's `git status` never shows them.
- Worktrees reach this same Brain through the same symlinks; never copy it per worktree.
- If the symlinks are missing or dangling, run `dotbrain wire` from the repo root.

## Rules

- Brain writes are agent-managed (git-tracked in dotbrain, so changes are revertable).
- Execution lives in beads. Work from `bd ready`; record multi-step plans as epics with
  `blocks` dependencies, not as markdown checklists.
- Use `CONTEXT.md` vocabulary when naming concepts in issues, plans, tests, and proposals.
  Do not drift to synonyms.
- If a proposed change conflicts with an ADR, call it out before proceeding.
- If `CONTEXT.md` or `adr/` are missing or empty, proceed silently — note the gap, don't
  scaffold them unasked.
- The code repo may be public; the Brain never is. Never mirror Brain content into the code
  repo — for a public need, derive a fresh audience-specific doc instead.
- Public-facing repo docs (README.md, repo-root AGENTS.md) must not expose private Brain
  paths or content. The only `.brain` reference allowed in the repo root is the one-line
  agent pointer to `.brain/AGENTS.md`.
- Never reference private Brain context from code, tests, comments, commit messages, or
  PR text: no ADR numbers, Brain paths, or decision-record identifiers in anything the
  public repo carries. State the rationale in plain terms instead; the ADR linkage stays
  in the Brain.

## Brain structure

- `CONTEXT.md` — domain vocabulary for this project
- `adr/` — Architecture Decision Records, one file per decision
- `prd/` — Product Requirements Documents, one initiative per file. Authored by `to-prd`,
  decomposed into bead epics by `to-issues`
- `agents/` — project-specific skill config. Skills are cross-project; the Brain only
  configures them
- `docs/` — derived docs, runbooks, reference material. Optional, never authoritative —
  canon wins
