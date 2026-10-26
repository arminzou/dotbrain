---
name: dotbrain
description: >
  The dotbrain operating convention — how a Brain, its work graph, and agent
  workspaces fit together, and the rules that bind work in a wired project. Invoke it
  to hand an agent the convention when the session-start hook did not.
---

*States the convention; changes nothing.* The document below is the exact text the
session-start hook injects as `.brain/DOTBRAIN.md`. Some harnesses never run that hook
(Cowork, Claude Desktop, an untrusted Codex hook), which is what this skill is for —
same document, delivered by hand.

## Who owns what

The convention describes the model; these skills act on it.

| To do this | Use |
|---|---|
| Create or repair `.brain` / `.beads` links | `wire-brain` |
| Create, claim, or close work items | `manage-work-graph` |
| Do an item or a finite batch of items | `run-execution` |
| Formalize an initiative, or record a decision | `to-design`, `grill-decisions` |
| Curate repository rules and private context | `curate-project-context` |

# DOTBRAIN.md

Shared rules for every dotbrain Brain, owned by dotbrain and synced by `dotbrain refresh`.
Do not edit per project; packaged template changes propagate to every Brain.

## Wiring

- The private Brain lives at `~/dotbrain/brainspaces/<name>/.brain`. Repo-root `.brain` and
  `.beads` are gitignored links into that Brainspace, shared by all worktrees; never copy it.
  Home sync records and shares Brain changes at turn end; agents need not commit them. Commit
  by hand in `~/dotbrain`, never the code repo, only for structural changes worth finding or
  reverting alone, such as retiring a Brainspace or closing a design.
- `.claude`, `.codex`, and `.agents/skills` are real checkout directories. Codex project skills
  go in `.agents/skills`; configuration and agents stay in `.codex`. Skills/Claude agents are symlinks;
  Codex agents are TOML marked `# dotbrain-managed-agent: v1`. Edit private sources; never
  commit local wiring or delivered copies.
- `dotbrain wire` attaches a main checkout or Git worktree; Git metadata connects worktrees
  to the main checkout's existing Brainspace without changing registration or declarations.
- Maintain the current wired checkout with `dotbrain refresh`, `dotbrain skills link`, or
  `dotbrain agents link`. Outside it, select `--project <name>`; asset linking also accepts a wired
  `--repo <checkout>`. Global assets require `--scope global`.
- `dotbrain unwire` removes checkout wiring, retaining data and other checkouts; retire Brainspaces via filesystem actions.
- Let the CLI compute relative links under `.claude` and `.agents/skills`; hand-counted paths can dangle.

## Rules

- Read `.brain/AGENTS.md` before substantial work for private rules/preferences; missing means defaults.
- Public `AGENTS.md` routes changes/reviews to root `RULES.md` if present, usable without a Brain.
- During implementation or review preparation, the lead or sole agent searches `.brain/RETRO.md`
  for task-relevant findings and passes applicable findings through existing assignments.
  Workers and reviewers reuse supplied findings; they need not read the whole notebook.
  Reuse findings in context. A missing notebook blocks nothing; do not scaffold it.
  Write `RETRO.md` by compare-and-swap: hash it on read, write a temporary file, and swap only
  if the hash is unchanged; on a conflict re-read and retry once, else keep the evidence in its
  record. Never lock it or overwrite a newer version.
- Brain writes are agent-managed; Git history in `~/dotbrain` makes them revertable.
- The work graph lives in beads. Work from `bd ready`; record multi-step plans as epics with
  `blocks` dependencies, not as markdown checklists. `manage-work-graph` maintains the graph;
  `run-execution` carries out an item or finite batch. Follow `manage-work-graph` for
  claims, actors, and who may change the graph or active design.
- PR approval, merge, and release stay human-owned. Follow `run-execution` for branches
  and HITL delivery, and `iterate-design` for authorized handoff delivery.
- Check human-gated items before each new item. Flag genuine unresolved scope, authority,
  acceptance, or design decisions; explicit operator gates and stricter instructions bind.
  Unflagged items are autonomous: work and accepted closure need no routine sign-off.
  A review alone does not create a human gate.
- Use `CONTEXT.md` vocabulary when naming concepts in issues, plans, tests, and proposals.
  Do not drift to synonyms.
- If a proposed change conflicts with an ADR, call it out before proceeding.
- If `CONTEXT.md` or `adr/` are missing or empty, proceed silently — note the gap, don't
  scaffold them unasked.
- Before explaining how the project works (build, runtime, deployment, integrations), search
  `.brain/docs/` for documented answers. These private references are not injected.
- Search the Brain by targeting `.brain/`: repo-root searches skip hidden, gitignored paths.
- The code repo may be public; the Brain never is. Never mirror Brain content into the code
  repo — for a public need, derive a fresh audience-specific doc instead.
- Public repo docs must not expose private content; derive standalone guidance. The standard
  `.brain/AGENTS.md` agent pointer is allowed.
- Never reference private Brain context from code, tests, comments, commit messages, or
  PR text: no ADR numbers, Brain paths, or decision-record identifiers. State the rationale
  in plain terms; the ADR linkage stays in the Brain.

## Working in loops

These invariants bind any iterative or autonomous execution, whatever skill or loop primitive
drives it:

- Verification, success, and acceptance criteria are human-owned; never weaken them to fit the build.
  During a loop, never edit Success Criteria or bead acceptance criteria. If they are wrong,
  ambiguous, or unmeetable, or a new scope/authority/criteria decision arises, stop affected work
  with evidence and recommend a decision through `grill-decisions`. Get human approval; record
  changes. Contain independent work.
- Autonomous iteration always has a hard stop — a retry cap, budget, or turn limit. When the stop
  is hit, report blocked with the attempt trail; do not keep iterating.
  Only the human authorizes a higher limit; keep the attempt history.
- Reuse complete approval without repeat `GO`; execution requests grant no missing authority.
  Follow `iterate-design` for contract validation, delivery, loop outcomes, and stop scopes.
- Review gates close only under `review-gate`'s rules.
- Beads are the state; the active design doc is the spec. State says where you are, the spec says
  where to go. Reread the spec every iteration, not just at loop start.

## Unknowns

The Brain exists to shrink the gap between the map (what the agent has been told — vocabulary,
decisions, rules) and the territory (the codebase and its real constraints). That gap is the
project's unknowns. Name them in four quadrants and use the terms exactly, so skills, issues, and
design docs speak one language:

- **Known knowns** — stated and settled. Live in `CONTEXT.md`, `adr/`, public `RULES.md`, and private `AGENTS.md`.
- **Known unknowns** — open questions you can name. Live in a design doc's `Known Unknowns` and in beads.
- **Unknown knowns** — tacit preferences and domain expectations, recognized only when shown.
  Surfaced by grilling and prototypes, then written into canon.
- **Unknown unknowns** — constraints, edge cases, and existing behavior you have not thought to
  consider. Surfaced by a blind-spot pass before implementation; caught mid-build as discoveries.

Cheap moves early — orient, grill, prototype — turn expensive late unknowns into known knowns.

`find-unknowns` is read-only: investigate facts first; report the cheapest next action and blocking
status or reasoned deferral. Choose reversible defaults within scope. `grill-decisions` owns human
preferences, authority, acceptance changes, consequential tradeoffs, and evidence-unsettled decisions.
These skills detail evidence and experiment limits. Active designs own uncertainty; Beads owns
execution state. `to-design` and `to-issues` detail verifiable seams and interface/resource prerequisites.

## Brain structure

- `AGENTS.md` — small private rules/preferences; `CLAUDE.md` is its relative symlink
- `DOTBRAIN.md` — shared Brain operations and retrieval, owned by dotbrain
- `RETRO.md` — optional private retrospective findings and evidence, retrieved for the task;
  established repository rules remain authoritative in public `RULES.md`
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
  (vocabulary). `close-design`, run on human request, checks actual PR merge evidence for shipment; until then
  design/epic stay active. Closed-unmerged is never shipped.
  Design frontmatter is one field set across every Brain: `lifecycle:` (required), `started:` and
  `ended:` (dates), `extends:` (a design this one builds on), `residue:` (ADR ids produced). Per-doc
  invented fields drift the vocabulary; say anything else in prose
- `docs/` — derived docs, runbooks, reference material. Optional, never authoritative —
  canon wins
- `learning/` — the operator's learning workspace for this project, owned by `teach-me`. Optional,
  never authoritative; learning paths and parked concepts live in `learn:` beads. When the user
  asks to park a concept for later learning, file it per `manage-work-graph`'s learning-beads
  reference
- `site/` — optional site settings (`site.yaml` nav), home (`index.md`), `configure.md`, and
  theme extensions. `dotbrain site` renders all Brain Markdown; `brain-site` maintains it

Skills are cross-project; the Brain only configures them. Skill *selection* lives in
`project.yaml` (`skills:`).
