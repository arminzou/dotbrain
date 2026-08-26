---
name: to-design
description: Formalize a multi-step initiative as a design doc in the Brain plus a tracking epic bead. Use when the user wants to design an initiative before decomposing it into work items, or arrives from grill-decisions or find-unknowns with a shape worth writing down.
---

# To Design

Synthesize the current conversation context and codebase understanding into a design doc under
`.brain/designs/`, then open the epic that tracks it. `DOTBRAIN.md` governs the doc over its whole
life; this skill covers authoring it.

## Process

### 1. Decide whether a design doc is the right shape

Use `to-design` when the initiative is multi-step, crosses modules or workflows, needs explicit
scope boundaries, or carries meaningful unknowns. Small, obvious, single-slice changes go straight
into beads instead.

If the initiative warrants an ADR, stop and run `grill-decisions` first. ADRs own durable decision
rationale; this doc owns the initiative's design, unknowns, and rollout.

Completion: you can state in one sentence why this initiative needs a doc rather than a bead,
or you have handed off to `grill-decisions`.

### 2. Read the local operating context

Read the nearest `AGENTS.md`, `DOTBRAIN.md`, `CONTEXT.md`, and the ADRs and design docs relevant to
the initiative. If `.brain/docs/` holds runbooks or reference notes bearing on the work, read those
too.

Completion: you can name the project's existing vocabulary for every concept this initiative
touches, and every ADR it interacts with.

### 3. Surface the unknowns before writing

Territory you have not inspected produces designs that break on contact. For unfamiliar codebases
or broad changes, run `find-unknowns` — it is the blind-spot pass, and its output seeds
`Known Unknowns` directly.

Where the area is already familiar, inspect the relevant modules yourself and produce a short
module sketch for the user: touched modules or systems, likely integration points, obvious
constraints, open questions.

Confirm the sketch with the user before creating anything.

Completion: every module the initiative touches is either inspected or listed as a known
unknown, and the user has confirmed the sketch.

### 4. Write the design doc

Copy `templates/design.md` to `.brain/designs/<slug>.md` and fill it in. The template carries the
section set, per-section authoring hints, and the lifecycle rules that apply after authoring.

The doc is born `lifecycle: draft`; flip it to `active` in step 5, once the epic exists.

Use `CONTEXT.md` vocabulary exactly for every concept it already names.

Completion: every section you kept is filled, every section you dropped is deleted along with
its hints, and each goal has a matching entry under `Success Criteria`.

### 5. Create the epic bead

Create the tracking epic and link it back to the design doc:

```bash
bd create "<Design title>" --type epic --description "See .brain/designs/<slug>.md" --spec-id design:<slug>
```

`--spec-id` links the execution graph back to the design doc. The epic stays private even when the
project configures a public tracker; attach `--external-ref` only when this initiative was promoted
from an already-existing public collaboration issue.

Set the doc's frontmatter to `lifecycle: active`.

Completion: the epic exists, its `--spec-id` matches the doc slug, and the doc reads
`lifecycle: active`.

### 6. Close

Summarize what was created: the design doc path and the epic bead ID. Recommend `to-issues` as the
next step.

## Boundaries

Three artifacts hold different material, and the design doc holds only the middle one:

- **Beads** hold execution: ready, blocked, done, dependencies, claims, acceptance, and
  slice-local implementation facts.
- **The design doc** holds the initiative's design story: shape and interfaces, verification
  criteria, unknowns, deviations, rollout.
- **ADRs** hold durable, cross-cutting, expensive-to-reverse decisions and their rationale. Link
  them from the design doc; state the rationale once, in the ADR.
