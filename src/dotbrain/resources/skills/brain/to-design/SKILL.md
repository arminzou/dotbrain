---
name: to-design
description: Turn the current conversation context into a design doc, save it to the Brain, and create an epic bead. Use when the user wants to formalize a multi-step initiative before decomposing into work items.
---

# To Design

Synthesize the current conversation context and codebase understanding into a **design doc** — one
sectioned file that folds the planning genres (motivation, spec, rollout) into a single artifact.
The design doc lives in the Brain as a point-in-time record; the epic bead tracks execution.

Do NOT interview the user — synthesize what you already know from the conversation. If you need
architecture or module-level clarity, explore the codebase.

## Process

### 1. Gather context

Read the existing Brain context for this project:

1. `.brain/CONTEXT.md` — domain vocabulary; use it throughout the design doc
2. `.brain/adr/` — relevant decisions in the area you're touching
3. Existing `.brain/designs/` — check for related designs

### 2. Explore the codebase

If you haven't already, explore the codebase to understand the current state. Sketch the major
modules you will need to build or modify.

Actively look for opportunities to extract **deep modules** — ones that encapsulate a lot of
functionality in a simple, testable interface which rarely changes (as opposed to shallow modules
that are thin wrappers or pass-throughs).

Present the module sketch to the user and confirm expectations before proceeding.

### 3. Write the design doc

Save it to `.brain/designs/<slug>.md`. Use a short kebab-case slug that captures the initiative
(e.g., `workflow-automation.md`, `api-rate-limiting.md`).

Fill only the sections this initiative needs — Non-goals and Open questions are optional; omit an
empty section rather than padding it.

<design-template>
---
status: active        # draft | active | shipped | superseded
date: <YYYY-MM-DD>
---

# <Feature / System Name>

## Motivation
The problem this solves, from the user's perspective. Lightweight PRD.

## Goals
What this should accomplish. Outcome bullets.

## Non-goals
What this intentionally will not solve.

## Design
How it works: the shape, key modules/interfaces, data flow. The technical core.

## Alternatives considered
Options weighed and why they lost. Feature-local tradeoffs live here.

## Implementation plan
Narrative phasing (phase 1 does X, phase 2 does Y). `to-issues` turns this into
bead epics; once decomposed, beads is the live tracker and this section is frozen.

## Open questions
Undecided points. Resolve, or promote to Design / an ADR as they close.
</design-template>

**A design doc is point-in-time.** It captures thinking at design time; it is not a living spec. Do
not include volatile implementation detail (exact file paths, code snippets) that goes stale — keep
Design at the shape/interface level. After the initiative ships, do not retro-edit the doc; write a
new one, or an ADR for a durable decision.

**If this initiative also warrants an ADR** (a fundamental, cross-cutting, or expensive-to-reverse
decision), write the ADR via `grill-decisions` and keep the design doc's *Alternatives considered*
thin, linking the ADR. The ADR owns the decision rationale; the design doc owns the plan. Do not
duplicate the alternatives in both.

### 4. Create the epic bead

Create an epic bead for this initiative:

```bash
bd create "<Design title>" --type epic --description "See .brain/designs/<slug>.md" --spec-id design:<slug>
```

The `--spec-id` link points from beads to the design doc. If a public issue tracker is configured,
also create a tracking issue there with a `needs-triage` label and link it via `--external-ref`.

### 5. Close

Summarize what was created — the design doc path and the epic bead ID — and recommend the next step
(running `to-issues` to decompose into task beads).

## Pitfalls

- **Do not include volatile implementation detail in the Design section.** File paths and code
  snippets go stale; keep it at the shape/interface level.
- **Do not duplicate an ADR's rationale in the design doc.** If a decision earns an ADR, link it and
  keep *Alternatives considered* thin.
- **Do not skip the module sketch step for unfamiliar codebases.** The decomposition depends on
  understanding the module boundaries.
- **Do not create the epic bead before the user confirms the module sketch.** The sketch validates
  the scope.
