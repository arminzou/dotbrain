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

A project created without a code checkout, using `dotbrain wire --no-repo --project <name>`.
It can still have an execution store. Add `--skip-beads` to create it without a tracker;
tracker-free projects can also have wired checkouts.

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
`dotbrain_` metadata keys holding its phase, attempts, and artifacts, and headed evidence comments.

### Lead, assignee, worker, agent team

An agent team is the lead and the workers it dispatches for one bounded execution. The lead
selects, integrates, checks, and closes items and is the only agent that changes the work graph
while delegated workers run. A worker carries out an assigned operation and reports back. The
assignee is the actor holding a work item's claim.

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

## Excluded terms

This glossary intentionally leaves out lower-level implementation jargon and private internal
phrasing. It is meant to explain the public conceptual model, not every CLI mutation path or
historical term.
