# Skills

dotbrain ships nine Brain-coupled skills: the operating manual for a wired project. They cover
wiring, planning, execution, triage, and Brain maintenance. Several are inspired by and adapted
from [mattpocock/skills](https://github.com/mattpocock/skills).

Skill selection is dotbrain-managed:

- required core skills ship with dotbrain in `src/dotbrain/resources/skills.yaml`
- operator-owned global extras live under the private dotbrain data root
- per-project extra skills are selected in `brainspaces/<name>/project.yaml`

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

The packaged skill registry lives at `src/dotbrain/resources/skills.yaml`.
