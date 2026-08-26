# Skills

The dotbrain plugin delivers its Brain-coupled skills: the operating manual for a wired project.
They cover wiring, planning, execution, triage, and Brain maintenance. Several are inspired by and adapted
from [mattpocock/skills](https://github.com/mattpocock/skills).

Skill linking is operator-managed:

- global skills are selected in `~/dotbrain/skills/skills.yaml`
- per-project skills are selected in `brainspaces/<name>/.brain/project.yaml`

## Setup

- **`wire-brain`** — provision or repair Brainspace wiring between a repo and its private Brain
- **`build-context`** — draft or normalize `AGENTS.md` and related context files

## Planning

- **`to-design`** — formalize a multi-step initiative into a living active design doc, save it to
  the Brain, and create an epic bead. Use when the work needs explicit design shape or a place to
  track unknowns before decomposition.
- **`to-issues`** — decompose a design doc into independently-workable bead tasks with acceptance
  criteria and dependencies, linking each bead back with `--spec-id design:<slug>`.
- **`grill-decisions`** — stress-test a plan against project vocabulary and decisions, then write
  durable results into `CONTEXT.md` and `adr/`.

## Execution

- **`operate-execution`** — inspect, claim, split, update, and close work in the private execution
  graph

## Triage And Review

- **`triage-public`** — classify public tracker items and promote ready work into private execution
- **`review-architecture`** — review the codebase for architectural deepening opportunities

## Authoring

- **`write-skills`** — create a new agent skill or improve an existing one: invocation choice,
  description writing, information hierarchy, and pruning

The plugin's skills are generated from `src/dotbrain/resources/skills/`.
