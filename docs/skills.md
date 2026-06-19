# Skills

dotbrain ships a small set of Brain-coupled skills. These are the operating manual for a wired
project: they tell an agent how to wire a repo, work with the private execution graph, triage
public issues, and maintain Brain context.

Skills are layered:

- dotbrain-managed required skills ship with the tool
- operator-owned skills live in the user's private dotbrain data root
- per-project skills are declared in `brainspaces/<name>/project.yaml` under `skills:`

dotbrain keeps the required core wired in place and layers operator/project skills on top.

## Required Core

The packaged baseline comes from
[src/dotbrain/resources/skills.yaml](/home/armin/repos/projects/dotbrain/src/dotbrain/resources/skills.yaml:1).

- `brain/wire-brain`
  Provisions or repairs the Brainspace wiring between a repo and its private Brain.
- `brain/operate-execution`
  Operates the private execution graph and recommends the next ready work item.
- `brain/enter-main-agent`
  Coordinates the optional main-agent and worker-worktree workflow.
- `brain/triage-public`
  Runs public issue intake and links accepted public work to private execution items.
- `brain/build-context`
  Drafts and normalizes `AGENTS.md` and related agent context files.
- `brain/review-architecture`
  Reviews the codebase for deeper architectural opportunities and feeds findings back into the Brain.
- `brain/grill-decisions`
  Stress-tests plans and writes clarified decisions into `CONTEXT.md` and ADRs.

## What Ships

The packaged skill set lives under
[src/dotbrain/resources/skills/brain/](/home/armin/repos/projects/dotbrain/src/dotbrain/resources/skills/brain).

- `build-context`
- `enter-main-agent`
- `grill-decisions`
- `operate-execution`
- `review-architecture`
- `triage-public`
- `wire-brain`

Each skill ships with its own `SKILL.md`, and some ship additional references for engine- or
tracker-specific mechanics.

## Configuration

There are two places where skills are configured:

- Global required skills are declared in `src/dotbrain/resources/skills.yaml`.
- Project-specific extra skills are declared in `brainspaces/<name>/project.yaml` under `skills:`.

Per-project `agents/` files do not choose skills. They only hold conventions shared by the skills,
such as `issue-tracker.md`.

## Rule Of Thumb

Use Markdown docs like this one to explain how the skills fit together. Let each skill's own
`SKILL.md` stay authoritative for the step-by-step operating procedure.
