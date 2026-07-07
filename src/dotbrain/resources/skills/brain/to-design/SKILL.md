---
name: to-design
description: Turn the current conversation context into a design doc, save it to the Brain, and create an epic bead. Use when the user wants to formalize a multi-step initiative before decomposing into work items.
---

# To Design

Synthesize the current conversation context and codebase understanding into a design doc in
`.brain/designs/`. An `active` design doc is a living unknowns ledger for the initiative. Beads
track execution; the design doc tracks the current design story while the initiative is underway.

## Process

### 1. Decide whether a design doc is the right shape

Use `to-design` when the initiative is multi-step, crosses modules or workflows, needs explicit
scope boundaries, or carries meaningful unknowns. Small, obvious, single-slice changes can go
straight into beads instead.

If the initiative warrants an ADR, stop and run `grill-decisions` first. ADRs own durable decision
rationale. The design doc owns the initiative's current design, unknowns, and rollout.

### 2. Read the local operating context

Read the nearest `AGENTS.md`, `DOTBRAIN.md`, `CONTEXT.md`, and the ADRs/design docs relevant to the
initiative. If `.brain/docs/` contains runbooks or reference notes that bear on the work, read
those too.

### 3. Sketch the solution before writing

For unfamiliar codebases or broad changes, inspect the relevant modules first and produce a short
module sketch for the user:

- touched modules or systems
- likely integration points
- obvious constraints
- open questions

Do not create the design doc or epic until the user confirms the sketch when the shape is still
uncertain.

### 4. Write the design doc

Create `.brain/designs/<slug>.md`.

Use the initiative title as the H1. Include frontmatter when the project uses it. Mark the doc as
`lifecycle: active` once execution starts. Author only the sections the initiative needs.

Common sections:

- `Motivation`
- `Goals`
- `Non-goals`
- `Current Design`
- `Verification / Success Criteria`
- `Known Unknowns`
- `Implementation Notes`
- `Deviations`
- `Human Decisions Needed`
- `Alternatives Considered`
- `Rollout`

Guidance:

- Keep the design at the interface and behavior level. Exact file paths and code snippets go stale.
- Define how progress and completion will be proven. Prefer concrete commands, checks, screenshots,
  metrics, or review gates. If no automated verifier exists, state the human/product judgment.
- Order `Current Design` by volatility: lead with the decisions most likely to change — data models,
  type interfaces, migration shape, UX flows — and put mechanical or obvious work last. Surfacing the
  volatile decisions first is what lets a reviewer catch a wrong turn cheaply.
- Put design-relevant discoveries back into the active design doc as implementation proceeds.
- Put slice-local execution facts in beads instead of the design doc.
- If a discovery becomes a durable, cross-cutting, expensive-to-reverse decision, promote it to an
  ADR.
- If the project vocabulary exists in `CONTEXT.md`, use it exactly.

### 5. Create the epic bead

Create the tracking epic and link it back to the design doc:

```bash
bd create "<Design title>" --type epic --description "See .brain/designs/<slug>.md" --spec-id design:<slug>
```

`--spec-id` links the execution graph back to the design doc. If the project also has a public
issue tracker, create a tracking issue there and link it with `--external-ref`.

### 6. Close

Summarize what was created: the design doc path and the epic bead ID. Recommend `to-issues` as the
next step.

## Pitfalls

- **Do not turn the design doc into a status board.** Ready, blocked, done, dependencies, claims,
  and acceptance stay in beads.
- **Do not include volatile implementation detail in `Current Design`.** Keep it at the
  shape/interface level.
- **Do not duplicate an ADR's rationale in the design doc.** Link the ADR and keep the design doc
  focused on the initiative.
- **Do not skip the module sketch step for unfamiliar codebases.** Good decomposition depends on
  understanding boundaries first.
