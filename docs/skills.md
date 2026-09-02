# Skills

The dotbrain plugin delivers its Brain-coupled skills: the operating manual for a wired project.
They cover wiring, planning, execution, triage, and Brain maintenance. Several are inspired by and adapted
from [mattpocock/skills](https://github.com/mattpocock/skills).

Skill linking is operator-managed:

- global skills are selected in `~/dotbrain/skills/skills.yaml`
- per-project skills are selected in `brainspaces/<name>/.brain/project.yaml`

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

- **`operate-execution`** — inspect, claim, split, update, and close work in the private execution
  graph
- **`iterate-design`** — run an active design doc through the agent's native loop mode: plan,
  implement, verify, reflect, stop on success or blocked

## Triage And Review

- **`curate-project-context`** — find and repair stale, duplicated, misplaced, unreachable, or
  leaking context across the public project and private Brain
- **`triage-public`** — classify public tracker items and promote ready work into private execution
- **`review-architecture`** — review the codebase for architectural deepening opportunities

## Authoring

- **`write-agent-docs`** — writing discipline for public project docs, private Brain material,
  user-owned skills, and guidance agents reach through pointers

## Installing Them

The skills arrive with the plugin, installed once per agent runtime rather than per repo. See
[getting-started.md](getting-started.md) for the install commands. Because the plugin installs at
user scope, its skills are available in every session, including repos that are not wired yet.

Edit bundled skills directly in [`plugin/skills/`](../plugin/skills/).
