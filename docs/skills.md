# Skills

The dotbrain plugin delivers its Brain-coupled skills: the operating manual for a wired project.
They cover wiring, planning, execution, triage, and Brain maintenance. Several are inspired by and adapted
from [mattpocock/skills](https://github.com/mattpocock/skills).

[The workflow](workflow.md) shows how they fit together.

Skill linking is operator-managed:

- global skills are selected in `~/dotbrain/skills/skills.yaml`
- per-project skills are selected in `brainspaces/<name>/.brain/project.yaml`

## Select and reconcile skills

Both scopes accept an individual skill or a bundle directory:

```yaml
# ~/dotbrain/brainspaces/my-app/.brain/project.yaml
skills:
  - my-collection/specific-skill
  - another-collection
```

```yaml
# ~/dotbrain/skills/skills.yaml
global_extra:
  - another-collection
```

A directory containing `SKILL.md` selects itself, even when it has descendant skills. Otherwise
dotbrain discovers descendant `SKILL.md` directories recursively, excluding `node_modules`.
Overlapping selections of the same source are deduplicated. Different sources mapping to the
same destination name, including case collisions on a case-insensitive filesystem, fail before
destination changes. Missing paths, non-directories, and empty bundles fail actionably.

```bash
dotbrain skills list                         # discover sources
dotbrain skills link                         # current wired checkout
dotbrain skills link --project my-app         # registered checkout
dotbrain skills link --scope global           # explicit global homes
dotbrain skills link --runtime codex           # declared Codex workspace only
```

Adding or removing skills from a selected bundle takes effect on the next reconciliation; the
declaration stays unchanged. Removed owned links are pruned, while foreign entries are preserved.
`projects show`, catalogs, and doctor use the same expanded selection.

## Setup

- **`wire-brain`** — provision or repair Brainspace wiring between a repo and its private Brain,
  including restoring a linked worktree's `.brain` and `.beads`. Installs the `dotbrain` CLI on
  first use if it is missing.
- **`dotbrain`** — the operating convention itself. The session-start hook injects it
  automatically; invoke it directly in runtimes where the hook does not run.

## Planning

- **`to-design`** — formalize a multi-step initiative into a living active design doc, save it to
  the Brain, and create an epic bead. Use when the work needs explicit design shape or a place to
  track unknowns before decomposition.
- **`to-issues`** — decompose a design doc into independently-workable bead tasks with acceptance
  criteria and dependencies, linking each bead back with `--spec-id design:<slug>`.
- **`grill-decisions`** — stress-test a plan against project vocabulary and decisions, then write
  durable results into `CONTEXT.md` and `adr/`.
- **`find-unknowns`** — surface blind spots and tacit assumptions in unfamiliar territory before
  committing to a design.
- **`close-design`** — drive a design doc to a terminal state: record evidence, promote residue to
  `adr/` and `CONTEXT.md`, close the epic.

## Execution

- **`manage-work-graph`** — file, inspect, claim, split, update, and close work items in the private
  work graph
- **`run-execution`** — carry out one work item or a fixed batch: dispatch workers, have each
  change reviewed independently, integrate, check, repair within limits, and escalate or recover
- **`iterate-design`** — run an active design doc through the agent's native loop mode: plan,
  implement, verify, reflect, deliver through a draft pull request that becomes ready for your
  review, and stop on success or blocked

## Triage And Review

- **`review-gate`** — run a durable review gate (code, simplification, or readiness) and record the
  outcome on the issue; a code review closes once you merge its pull request, and other reviews
  close with you
- **`curate-project-context`** — find and repair stale, duplicated, misplaced, unreachable, or
  leaking context across the public project and private Brain
- **`triage-public`** — classify public tracker items and promote ready work into private execution
- **`review-architecture`** — review the codebase for architectural deepening opportunities

## Authoring

- **`write-agent-docs`** — writing discipline for public project docs, private Brain material,
  user-owned skills, and guidance agents reach through pointers

## Brain Site

- **`brain-site`** — set up, maintain, and build a Brain's private site with `dotbrain site`: arrange
  the sidebar, preview, fix a failed build, and write pages with VitePress and Mermaid syntax

## Learning

See [Learning your project](learning.md) for learning paths, parked concepts, and session continuity.

- **`teach-me`** — teach the operator their project from its Brain over many sessions: explain in
  conversation, walk a learning path tracked as a `learn:` bead, record what was demonstrated, and
  capture approved lessons into `.brain/learning/`

## Subagents

Alongside the skills, dotbrain ships Brain-aware subagents: `worker`, `reviewer`,
`verifier`, and `researcher`. See
[Session context](session-context.md#subagents).

## Installing Them

The skills arrive with the plugin, installed once per agent runtime rather than per repo. See
[getting-started.md](getting-started.md) for the install commands. Because the plugin installs at
user scope, its skills are available in every session, including repos that are not wired yet.

Edit bundled skills directly in [`plugin/skills/`](https://github.com/arminzou/dotbrain/tree/main/plugin/skills).
