---
name: dotbrain-convention
description: >
  The dotbrain operating convention — how a Brain, its execution graph, and agent
  workspaces fit together, and the rules that bind work in a dotbrain-wired project.
  Use when working in a repo that has a .brain directory, when a session did not
  receive the convention as injected context (Cowork, Claude Desktop, or an untrusted
  Codex hook), or when checking what dotbrain expects before changing wiring,
  designs, ADRs, or issues.
---

# DOTBRAIN.md

Shared operating rules for all dotbrain brains. Owned by dotbrain; rehydrated by
`dotbrain refresh`. Do not edit per project — changes to the packaged dotbrain
Brain template propagate to every brain.

## Wiring

- This Brain lives in the private dotbrain home at
  `~/dotbrain/brainspaces/<name>/.brain`, not in the code repo.
- Repo-root `.brain` and `.beads` are gitignored symlinks into that Brainspace. `.claude` and
  `.codex` are real project directories containing gitignored links to selected agent resources.
  Those links are local machine wiring: never commit them to the code repo.
- Brain changes are committed in `~/dotbrain`. The code repo's `git status` never shows them.
- Worktrees reach this same Brain through their own `.brain` and `.beads` symlinks; never copy it
  per worktree.
- Create worktrees outside the repo with `git worktree add ../worktrees/<name> -b <name>`.
- In the main checkout, repair missing or dangling links with `dotbrain wire` from the repo root.
- In a git worktree with no `.brain`, invoke the plugin-delivered `wire-worktree` skill. It derives
  the main checkout from Git and creates real `.brain` and `.beads` symlinks without the CLI.

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

## Working in loops

These invariants bind any iterative or autonomous execution, whatever skill or loop primitive
drives it:

- Verification, success, and acceptance criteria are human-owned. They can change, but only through
  the human: surface the proposed wording and the reason, get approval, then record what changed.
  Where no human is present to approve — an autonomous loop — that is a stop condition, not a
  licence to decide. What is ruled out in every workflow is an agent weakening or rewriting them on
  its own to match what the build does.
- Autonomous iteration always has a hard stop — a retry cap, budget, or turn limit. When the stop
  is hit, report blocked with the attempt trail; do not keep iterating.
- Irreversible or outward-facing actions — merge, push, deploy, publish, dependency changes — end
  the loop and go to the human, whatever work item is in flight.
- Automation-handoff / agent-driven loop work runs on a dedicated branch, never directly on
  `main`; manual turn-by-turn work needs no branch — it is reviewed as it happens.
- Beads are the state; the active design doc is the spec. State says where you are, the spec says
  where to go. Reread the spec every iteration, not just at loop start.

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
- `project.yaml` — per-project skill selection and engine/tracker config
- `adr/` — Architecture Decision Records, one file per decision
- `designs/` — design docs, one initiative per file. Each design doc carries a `lifecycle:` field:
  `draft`, `active`, `shipped`, `abandoned`, or `superseded`. Agents must update lifecycle when the
  document's mutability changes. While a design is `active`, it is the living design authority for
  the initiative: current design, verification / success criteria, known unknowns, deviations, and
  design-relevant implementation discoveries live here. Authored by `to-design`, decomposed into
  bead epics by `to-issues`.
  Beads still own execution state. Once a design is `shipped`, `abandoned`, or `superseded`, it
  freezes as a point-in-time record; durable residue lands in `adr/` (decisions) and `CONTEXT.md`
  (vocabulary). Driving a design to a terminal state is `close-design`'s job.
  Design frontmatter is one field set across every Brain: `lifecycle:` (required), `started:` and
  `ended:` (dates), `extends:` (a design this one builds on), `residue:` (ADR ids produced). Per-doc
  invented fields drift the vocabulary apart; say anything else in prose
- `docs/` — derived docs, runbooks, reference material. Optional, never authoritative —
  canon wins

Skills are cross-project; the Brain only configures them. Skill *selection* lives in
`project.yaml` (`skills:`); project tracker conventions live in `AGENTS.md` under Project.
