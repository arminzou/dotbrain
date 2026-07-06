# Skills

dotbrain ships nine Brain-coupled skills: the operating manual for a wired project. They cover
wiring, planning, execution, triage, and Brain maintenance.

Several of these skills are inspired by and adapted from
[mattpocock/skills](https://github.com/mattpocock/skills).

Skills are layered:

- dotbrain-managed required skills ship with the tool
- operator-owned skills live in the user's private dotbrain data root
- per-project skills are declared in `brainspaces/<name>/project.yaml` under `skills:`

dotbrain keeps the required core wired in place and layers operator/project skills on top.

## Setup

- **`wire-brain`** — provision or repair Brainspace wiring between a repo and its private Brain.
  Run when starting a project, connecting an existing repo, or repairing dangling symlinks.
- **`build-context`** — draft or normalize `AGENTS.md` and related agent context files. Run when
  bootstrapping a new project's agent instructions or repairing drift.

## Planning

- **`to-design`** — formalize a multi-step initiative into a design doc, save it to the Brain, and
  create an epic bead. Run when an idea is ready to become structured work.
- **`to-issues`** — decompose a design doc into independently-workable bead tasks with acceptance
  criteria and dependencies. Run after `to-design`.
- **`grill-decisions`** — stress-test a plan against the project's vocabulary and existing
  decisions, then write clarified choices into `CONTEXT.md` and `adr/`.

## Execution

- **`operate-execution`** — inspect the ready frontier, claim a work item, and record discoveries
  back into the execution graph. The primary skill for driving daily work.
- **`enter-main-agent`** — activate the two-agent protocol from the main checkout: stay parked
  on `main`, dispatch worker slices, review and land results.

## Triage and review

- **`triage-public`** — intake public issues (GitHub, Linear, Jira), classify them, and link
  accepted work to private execution items.
- **`review-architecture`** — review the codebase for deeper architectural opportunities and feed
  findings back into the Brain.

## Configuration

There are two places where skills are configured:

- Global required skills are declared in `src/dotbrain/resources/skills.yaml`.
- Project-specific extra skills are declared in `brainspaces/<name>/project.yaml` under `skills:`.

Per-project `agents/` files do not choose skills. They only hold conventions shared by the
skills, such as `issue-tracker.md`.

## Rule Of Thumb

Use Markdown docs like this one to explain how the skills fit together. Let each skill's own
`SKILL.md` stay authoritative for the step-by-step operating procedure.
