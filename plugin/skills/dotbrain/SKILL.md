---
name: dotbrain
description: >
  The dotbrain operating convention — how a Brain, its work graph, and agent
  workspaces fit together, and the rules that bind work in a wired project. Invoke it
  to hand an agent the convention when the session-start hook did not.
disable-model-invocation: true
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

Shared operating rules for all dotbrain brains. Owned by dotbrain; synced by
`dotbrain refresh`. Do not edit per project — changes to the packaged dotbrain
Brain template propagate to every brain.

## Wiring

- The private Brain lives at `~/dotbrain/brainspaces/<name>/.brain`. Repo-root `.brain` and
  `.beads` are gitignored links into that Brainspace, shared by all worktrees; never copy it.
  Commit Brain changes in `~/dotbrain`, not the code repo.
- `.claude` and `.codex` are real checkout directories. Selected skills and Claude agents are
  symlinks; Codex agents are real TOML files marked `# dotbrain-managed-agent: v1`.
  Customize private sources. Never commit local wiring or delivered copies to the code repo.
- `dotbrain wire` attaches a main checkout or Git worktree; Git metadata connects worktrees
  to the main checkout's existing Brainspace without changing registration or declarations.
- Maintain the current wired checkout with `dotbrain refresh`, `dotbrain skills link`, or
  `dotbrain agents link`. Outside it, select `--project <name>`; asset linking also accepts a wired
  `--repo <checkout>`. Global assets require `--scope global`.
- `dotbrain unwire` detaches one checkout, retaining private data, other checkouts, and user files.
  Retire Brainspaces through filesystem actions.
- Let the CLI compute relative links under `.claude` and `.codex`; hand-counted paths can dangle.

## Rules

- Public `AGENTS.md` routes making/reviewing changes to tracked root `RULES.md`, usable without a Brain.
- During implementation or review preparation, the lead or sole agent searches `.brain/RETRO.md`
  for task-relevant findings and passes applicable findings through existing assignments.
  Workers and reviewers reuse supplied findings; they need not read the whole notebook.
  Reuse findings while they remain in context. A missing notebook blocks nothing; do not scaffold it.
- Brain writes are agent-managed (git-tracked in dotbrain, so changes are revertable).
- The work graph lives in beads. Work from `bd ready`; record multi-step plans as epics with
  `blocks` dependencies, not as markdown checklists. `manage-work-graph` maintains the graph;
  `run-execution` carries out an item or finite batch. While delegated workers run, only the
  lead changes the work graph or the active design doc; the lead is the agent running that
  execution.
- Both the HITL and handoff workflows run on a dedicated branch and land through a review
  surface: a PR, or the branch diff where the project hosts no PRs. Parallel workers integrate
  into that branch, never into `main`. In the HITL workflow, propose the branch at the first
  bounded execution; it may span several bounded executions. Reuse approval before pushing or opening a PR;
  ask only for missing authority. Merge stays human-owned; PR approval and release too.
  Local HITL landing requires explicit human instruction, recorded
  by the lead; it is never the default.
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
- Public-facing repo docs (README.md, repo-root AGENTS.md, RULES.md) must not expose private
  Brain paths or content. Derive independently understandable public guidance.
- Never reference private Brain context from code, tests, comments, commit messages, or
  PR text: no ADR numbers, Brain paths, or decision-record identifiers in anything the
  public repo carries. State the rationale in plain terms instead; the ADR linkage stays
  in the Brain.

## Working in loops

These invariants bind any iterative or autonomous execution, whatever skill or loop primitive
drives it:

- Verification, success, and acceptance criteria are human-owned; never weaken them to fit the build.
  New scope/authority/criteria decisions stop affected work with evidence and a recommendation.
  Get human approval; record changes. Contain independent work.
- Autonomous iteration always has a hard stop — a retry cap, budget, or turn limit. When the stop
  is hit, report blocked with the attempt trail; do not keep iterating.
- Reuse complete approval without repeat `GO`; execution requests grant no missing authority.
  `iterate-design` validates scope, branch/base, checks/UAT, reviews, provider/auth, PR authorization
  and finite limits; preserve overrides and remaining limits on resume. Check credentials privately;
  availability grants no authority. Delivery: a draft PR at the first push, one mention of the human
  for each blocked stop. `FINAL`: agreed work, reviews, acceptance/UAT complete; ready-for-review PR
  requests human review. Unauthorized actions end the loop and go to the human.
- The lead closes accepted work and reviews without routine human sign-off, before PR merge:
  required verdict/evidence at the exact integrated revision, blocking findings resolved and other
  findings dispositioned. Simplify closes on dispositions, stays non-blocking. Explicit gates bind.
  Closure never merges the target branch and never automatically invokes `close-design`. Details:
  `manage-work-graph/references/review-beads.md`.
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

`find-unknowns` is read-only: investigate facts first; report the cheapest next action and blocking
status or reasoned deferral. Choose reversible defaults within scope. `grill-decisions` owns human
preferences, authority, acceptance changes, consequential tradeoffs, and evidence-unsettled decisions.
These skills detail evidence and experiment limits. Active designs own uncertainty; Beads owns
execution state. `to-design` and `to-issues` detail verifiable seams and interface/resource prerequisites.

## Brain structure

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
  (vocabulary). Manual `close-design` checks actual PR merge evidence for shipment; until then
  design/epic stay active. Closed-unmerged is never shipped.
  Design frontmatter is one field set across every Brain: `lifecycle:` (required), `started:` and
  `ended:` (dates), `extends:` (a design this one builds on), `residue:` (ADR ids produced). Per-doc
  invented fields drift the vocabulary apart; say anything else in prose
- `docs/` — derived docs, runbooks, reference material. Optional, never authoritative —
  canon wins
- `learning/` — the operator's learning workspace for this project, owned by `teach-me`. Optional,
  never authoritative; learning paths and parked concepts live in `learn:` beads. When the user
  asks to park a concept for later learning, file it per `manage-work-graph`'s learning-beads
  reference
- `site/` — the Brain site's settings (`site.yaml`, whose nav is the sidebar), its home page
  `index.md`, dotbrain's manual `configure.md`, and optional theme extensions. Optional; `dotbrain site` renders every Markdown file
  in the Brain as a page, and `brain-site` maintains it

Skills are cross-project; the Brain only configures them. Skill *selection* lives in
`project.yaml` (`skills:`). Public repository instructions route changes and reviews to `RULES.md`.
