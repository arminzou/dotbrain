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
- Wire, refresh, link, and unwire checkouts through the `dotbrain` CLI; `wire-brain` covers the
  commands and selection flags. Worktrees share the main checkout's Brainspace. Let the CLI
  compute relative links under `.claude` and `.agents/skills`; hand-counted paths can dangle.

## Rules

- Read `.brain/AGENTS.md` before substantial work for private rules/preferences; missing means defaults.
- Public `AGENTS.md` routes changes/reviews to root `RULES.md` if present, usable without a Brain.
- Before implementation or review, the lead or sole agent searches `.brain/RETRO.md` once per
  task or batch and passes applicable practices through assignments; at completion it records
  transferable ones per `run-execution`. Workers and reviewers reuse supplied findings; they need
  not read the whole notebook. A missing notebook blocks nothing; do not scaffold it.
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
- The code repo may be public; the Brain never is. Never mirror Brain content into the repo;
  for a public need, derive fresh standalone guidance (the standard `.brain/AGENTS.md` pointer is
  allowed). Code, tests, comments, commits, and PR text carry no private Brain context: no ADR
  numbers, Brain paths, decision-record identifiers, or paraphrased private incidents and
  decisions. State the rationale in plain terms; the linkage stays in the Brain.

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

Choose reversible defaults within scope; take human preferences, authority, acceptance changes,
and consequential tradeoffs to `grill-decisions`. Active designs own uncertainty; Beads owns
execution state.

## Brain structure

- `AGENTS.md` — small private rules/preferences; `CLAUDE.md` is its relative symlink
- `DOTBRAIN.md` — shared Brain operations and retrieval, owned by dotbrain
- `RETRO.md` — optional private retrospective findings and evidence, retrieved for the task;
  established repository rules remain authoritative in public `RULES.md`
- `CONTEXT.md` — domain vocabulary for this project
- `project.yaml` — per-project skill selection and engine/tracker config
- `adr/` — Architecture Decision Records, one file per decision
- `designs/` — design docs, one initiative per file, each with a `lifecycle:` field (`draft`,
  `active`, `shipped`, `abandoned`, `superseded`) kept current as its mutability changes. An
  `active` design is the initiative's living authority for design, criteria, unknowns, and
  deviations; beads own execution state. Lifecycle rules live in `designs/README.md`; the
  frontmatter vocabulary lives in `to-design`'s design template
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
