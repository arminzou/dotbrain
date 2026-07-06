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
- `.brain/docs/` holds project-scoped knowledge (runbooks, references, derived notes) that
  is not auto-injected into context. Before answering how this project builds, runs, deploys,
  integrates, or otherwise works, check and search `.brain/docs/` first — do not infer from
  the public repo or generic conventions when the Brain has a documented answer.
- The code repo may be public; the Brain never is. Never mirror Brain content into the code
  repo — for a public need, derive a fresh audience-specific doc instead.
- Public-facing repo docs (README.md, repo-root AGENTS.md) must not expose private Brain
  paths or content. The only `.brain` reference allowed in the repo root is the one-line
  agent pointer to `.brain/AGENTS.md`.
- Never reference private Brain context from code, tests, comments, commit messages, or
  PR text: no ADR numbers, Brain paths, or decision-record identifiers in anything the
  public repo carries. State the rationale in plain terms instead; the ADR linkage stays
  in the Brain.

## Unknowns

The Brain exists to shrink the gap between the map (what the agent has been told — vocabulary,
decisions, rules) and the territory (the codebase and its real constraints). That gap is the
project's unknowns. Name them in four quadrants and use the terms exactly, so skills, issues, and
design docs speak one language:

- **Known knowns** — stated and settled. Live in `CONTEXT.md`, `adr/`, and `AGENTS.md`.
- **Known unknowns** — open questions you can name. Live in a design doc's `Known Unknowns` and in beads.
- **Unknown knowns** — tacit preferences and domain expectations, recognized only when shown.
  Surfaced by grilling and prototypes, then written into canon.
- **Unknown unknowns** — constraints, edge cases, and existing behavior you have not thought to
  consider. Surfaced by a blind-spot pass before implementation; caught mid-build as discoveries.

Cheap moves early — orient, grill, prototype — turn expensive late unknowns into known knowns.

## Brain structure

- `CONTEXT.md` — domain vocabulary for this project
- `adr/` — Architecture Decision Records, one file per decision
- `designs/` — design docs, one initiative per file. Each design doc carries a `lifecycle:` field:
  `draft`, `active`, `shipped`, `abandoned`, or `superseded`. Agents must update lifecycle when the
  document's mutability changes. While a design is `active`, it is the living design authority for
  the initiative: current design, known unknowns, deviations, and design-relevant implementation
  discoveries live here. Authored by `to-design`, decomposed into bead epics by `to-issues`.
  Beads still own execution state. Once a design is `shipped`, `abandoned`, or `superseded`, it
  freezes as a point-in-time record; durable residue lands in `adr/` (decisions) and `CONTEXT.md`
  (vocabulary)
- `docs/` — derived docs, runbooks, reference material. Optional, never authoritative —
  canon wins

Skills are cross-project; the Brain only configures them. Skill *selection* lives in
`project.yaml` (`skills:`); project tracker conventions live in `AGENTS.md` under Project.
