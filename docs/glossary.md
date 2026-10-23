# Glossary

## Core terms

### Dotbrain

The tool itself. dotbrain wires a private Brainspace and skill/runtime setup into a code repo
without moving that private state into the repo.

### Dotbrain home

The private data root, conventionally `~/dotbrain`, that holds every project's Brainspace under
`brainspaces/`, user-managed skills under `skills/`, subagent sources under `agents/`, and global
`config.yaml`. It is a separate Git repository from your code checkouts. Set `DOTBRAIN_HOME` or
pass `--home <path>` to select a different location.

### Brainspace

The private per-project home under `~/dotbrain/brainspaces/<name>/`. A Brainspace contains the
project's Brain (`.brain/`) and, when enabled, its execution store (`.beads/`). Agent workspaces
(`.claude/` and `.codex/`) are real directories in the code checkout.

### Brainspace links

The gitignored links placed in a repo that point back to the private Brainspace. Typical links are
`.brain` and `.beads`; `.claude` and `.codex` are project-owned directories with individually
ignored dotbrain resources.

### Brain

The durable knowledge layer for a project. The Brain holds project context, decisions, and
agent-facing conventions. In dotbrain terms, the Brain is narrower than the full Brainspace.

### Brain-only project

A retired kind of project with no code checkout. `dotbrain wire --no-repo` no longer exists: every
project has a repository as its working home. That repository can be private and hold only
documents. To migrate a Brain-only Brainspace, run `dotbrain wire --project <name>` from its new
repository, or move the Brainspace out of `brainspaces/` to archive it. Add `--skip-beads` to
create a project without a tracker.

### ADR

An Architecture Decision Record in the Brain's `adr/`. One file per decision that is hard to
reverse, surprising without context, and the result of a real trade-off.

### Design doc

One initiative's design in the Brain's `designs/`. Its `lifecycle` is `draft`, `active`, `shipped`,
`abandoned`, or `superseded`. An active design is the living spec; a terminal one is a record.
See [The workflow](workflow.md).

### Bead

One issue in the Beads execution store. Epics group beads, and `blocks` dependencies decide which
are ready.

### Brain site

The private, local documentation site `dotbrain site` renders from a Brain. See
[Brain site](brain-site.md).

### `config.yaml`

The global dotbrain config file, usually at `~/dotbrain/config.yaml`. It holds machine-wide
defaults such as shared beads server settings.

### `project.yaml`

The per-project config file at `~/dotbrain/brainspaces/<name>/.brain/project.yaml`. It declares project-level
settings such as execution engine choice, public tracker choice, seeded agent workspaces, beads
deviations, and extra skills.

### Execution engine

The backend that holds the private work graph for a project. Today that is beads, but the term
describes the role rather than a specific implementation.

### Execution store

The live state managed by the execution engine. In practical terms, this is where open work,
dependencies, readiness, and closure state live.

### Work graph

The work items in the execution store and the dependency edges between them: what work exists and
what it waits on. The ready frontier is the set of open items with no open blockers.

### Execution graph

How an agent team carries out a fixed set of work items: dispatch, integration, checks, and the
order in which items close and release their dependents. It lives in the lead's session, not in
the tracker.

### Execution record

The recoverable facts on a work item under execution: its native status and assignee, a few
`dotbrain_` metadata keys holding its phase, attempts, and artifacts, and headed evidence comments,
including its item reviews.

### Human-in-the-Loop (HITL) workflow

The workflow in which you direct the agent step by step and see changes as they happen. The agent
returns to you after each bounded execution, and its work still reaches `main` through a pull
request you review. See [The workflow](workflow.md#_5-work-the-issues).

### Handoff workflow

The workflow in which an agent continues within a contract you approved, with an explicit `GO` or by reusing an approved contract,
until it finishes, reaches a human gate, or hits a hard stop. `iterate-design` runs it and delivers
the work through a pull request that becomes ready for your review.

### Execution mode

How many agents write at once during one bounded execution: sequential execution, one writer at a
time, or parallel execution, two or more writing workers each in its own worktree. Either workflow
can use either mode.

### Bounded execution

One run of `run-execution` over a fixed set of work items. It ends when every item is closed, or
open with a recorded blocker, human gate, or cancellation.

### Item review

An independent code review of one work item's change to code, tests, build or CI config, or agent
instructions, by a reviewer agent that wrote none of it, before the item closes. The reviewer
records its verdict, `APPROVE` or `CHANGES`, on the work item itself.

### Lead, assignee, worker, agent team

An agent team is the lead and the workers it dispatches for one bounded execution. The lead
selects, integrates, checks, and closes items and is the only agent that changes the work graph
while delegated workers run. A worker carries out an assigned operation and reports back. The
assignee is the actor holding a work item's claim; a worker keeps its claim until the item closes,
while the lead integrates and closes it.

### Agent runtime

The coding agent environment dotbrain wires into, such as Claude Code or Codex.

### Agent workspace

The runtime-specific workspace directory in a repo, such as `.claude/` or `.codex/`. dotbrain links
only its selected resources inside it.

### Public tracker

The outward-facing issue system used for public intake and contributor collaboration, such as
GitHub Issues. Existing public issues may be promoted into the private work graph with a
provenance link. Private designs, epics, and work items are never projected outward as public
tracking issues; a PR can provide a public review surface without one.

### Worktree

A git worktree that shares the same repo history but has its own working directory. In dotbrain,
`dotbrain wire` uses Git metadata to connect it directly to the main checkout's existing Brainspace.

### Bootstrap

The machine-level setup step run by `dotbrain bootstrap`. It seeds global config and links global
skills.

### Skill

A reusable agent capability with its own instructions and, sometimes, reference material.

### Brain-coupled skill

A skill that operates directly on a project's Brain or execution state. dotbrain ships a required
core of these skills as part of its operating model.

### Adopter repo

A normal code repo that dotbrain wires to a private Brainspace. The adopter repo stays focused on
the code; the Brain and execution state live outside it.

### Derive

To create a public-facing explanation or artifact from private source material without exposing the
private source directly. dotbrain uses this boundary to keep Brains private while still publishing
docs or tooling publicly.

## Delivery and verification

### Home sync

The exchange of the dotbrain home's Git history with its own private remote through
`dotbrain sync`. It records uncommitted home changes before exchanging history.
Tracker sync (`dotbrain beads sync`) is separate and pulls only.

### Plugin and packaged subagent

A plugin is the runtime-native package delivering dotbrain's shared skills, convention,
and runtime integration. A packaged subagent is an agent definition shipped by dotbrain:
the writing `worker`, or the read-only `researcher`, `reviewer`, and `verifier`.
The packaged worker carries out an assignment and commits its candidate; the lead handles delivery.
See [Session context](session-context.md#subagents) for runtime discovery and delivery.

### Review bead

A work item recording a design-level or standalone review: its scope, standard, findings,
evidence, verdict when applicable, and disposition of each finding. Item and integration
reviews are recorded on their member work items instead of creating a separate review bead.

### Integration review

An independent code review of a group of provisionally combined work items at one exact
revision. It covers each member's acceptance criteria, affected consumers, and interactions
between the changes before those items close or release dependent work.

### Integration candidate

An isolated branch holding proposed changes based on an accepted revision. Review and checks
cover its exact head before the lead promotes it onto the delivery branch. Changed patches
or integration context require refreshed evidence.

### Accepted head

The commit covered by a passing review and its required checks: the head of a review bead's
recorded range, or a verified work item's recorded integrated revision. `dotbrain check-head`
compares the delivery branch with that revision. See the [CLI reference](cli-reference.md#dotbrain-check-head).

### Delivery branch

The dedicated branch containing accepted results. Promotion fast-forwards it to an accepted
candidate's exact head; failed or uncovered candidates remain separate.

### Checkpoint

A bounded implementation step and its narrow check within an execution. Retry history is
tracked separately for each named checkpoint, such as tests or item review. A checkpoint
is not itself a work item or commit; its check belongs to the agent making the change.

### Verifier gate and verification evidence

A verifier gate is the agreed mechanical pass/fail check, such as tests, a build, or a metric.
Verification evidence records what actually ran, its output and gaps, and the revision and
environment it covers. The verifier role runs a gate and reports that evidence; review adds
judgment. See [The workflow](workflow.md) for who runs each tier of checks.

### Acceptance and UAT

Acceptance means the agreed criteria and evidence permit accepting an item or integrated
candidate onto the delivery branch. UAT (user acceptance testing) exercises agreed user
journeys in a named runtime, version, and OS environment. Agents can run and record these
checks; the human still owns PR approval and merge.

### Review surface

Where a change is presented for review: usually a PR, or the branch diff for a project
without PR hosting. The full suite and audience-safe verification evidence belong there.

### Oracle

The written standard a review judges against: applicable decisions, design goals, criteria,
and rules. It is fixed before the review so the result answers the original question.

### Canon and durable residue

Canon is the project's authoritative vocabulary, decisions, and rules, as distinct from
derived explanations. Durable residue is knowledge from a completed design that remains
useful beyond that initiative and is placed in the appropriate vocabulary, decision, or
rules document. See [Design closeout](workflow.md) for the lifecycle.

## Excluded terms

This glossary intentionally leaves out lower-level implementation jargon and private internal
phrasing. It is meant to explain the public conceptual model, not every CLI mutation path or
historical term.
