---
name: close-design
description: Drives a design doc to a terminal lifecycle state — records achieved evidence, promotes residue to adr/ and CONTEXT.md, stamps frontmatter, closes the epic. Use when an initiative ships, is abandoned or superseded, when a stale `active` doc needs classifying, or when sweeping `.brain/designs/` for docs that never closed out.
---

# Close Design

A design doc is `active` only while it is the living design authority. Once the work lands, is
dropped, or is replaced, the doc freezes and its durable residue belongs in canon. This skill owns
that transition.

`operate-execution` reaches this skill when the last open slice under a design-linked epic closes.
It is also invoked directly for the sweep and retroactive cases below.

## Stop before you start

- The initiative is still live — a doc with open slices under its epic is `active` by definition,
  and freezing it strands the work. Only the sweep case below reads a still-`active` doc.
- You are here to close a bead, not a doc. Closing the epic is the last act of this transition,
  never a way to manage work.

## Branches

| Trigger | Terminal state |
|---|---|
| Work landed and verification passed | `shipped` |
| Work dropped without landing | `abandoned` |
| A newer design replaced this one | `superseded` |
| Sweep: `active` doc that went quiet | whichever of the three fits |
| Retroactive: already-terminal doc that never harvested | state unchanged, residue promoted |

## Process

### 1. Establish the terminal state

For a single doc, read it and the beads it links:

```bash
bd list --spec "design:<slug>" --status open,in_progress,blocked,deferred,closed --json
```

`--spec` matches by *prefix*, so a slug that prefixes another slug over-matches (`design:qa-bank`
also returns `design:qa-bank-variety-pass` items). Filter the result to an exact `spec_id` before
drawing any conclusion about which slices belong to this doc. `--spec-id` is a `bd create` flag and
is not accepted by `bd list`.

For a sweep, enumerate every doc in `.brain/designs/` with its lifecycle and the state of its epic.
An `active` doc whose slices are all closed shipped and was never stamped; one whose epic was
dropped is abandoned; one whose design was replaced is superseded, and names its replacement.

Present the classification and confirm before writing anything. A terminal state is a claim about
what happened, and getting it wrong buries the initiative under the wrong label.

Completion: every doc in scope carries a proposed terminal state with the evidence behind it,
and the user has confirmed the set.

### 2. Record the verification evidence achieved

Under `Verification Evidence`, write what was actually run and what it returned, one entry per
criterion in `Success Criteria`. Leave `Success Criteria` itself untouched here: at close-out the
bar is whatever it was when the work ran, so an unmet criterion is recorded as unmet rather than
reworded to fit. The split exists so recording an outcome can never edit the bar it answers to.

Where a criterion was dropped or changed mid-flight, that belongs under `Deviations` with the
reason.

Where a criterion went unmet and the work shipped anyway, say so plainly. A gate that was quietly
skipped is the one most worth knowing about later.

For an `abandoned` or `superseded` doc, record instead what was learned before the work stopped.

Completion: every criterion in `Success Criteria` has a matching entry under
`Verification Evidence` — passed, failed, dropped, or never run.

### 3. Triage the residue

Every discovery the initiative produced lands in exactly one place:

- **`adr/`** — a durable, cross-cutting, expensive-to-reverse decision, including a rejection. Why
  an approach was abandoned is often worth more than why one was chosen.
- **`CONTEXT.md`** — a concept the project now names and will keep naming.
- **`.brain/docs/`** — a maintained "how it works now" description, which the frozen design doc is
  not.
- **Nowhere** — slice-local facts that die with their beads.

Write the ADR ids you created into the doc's `residue:` frontmatter, so provenance survives in both
directions.

Completion: every entry under `Known Unknowns`, `Deviations`, and `Implementation Notes` has
been placed in one of the four, and `residue:` lists every ADR the initiative produced.

### 4. Stamp and close

Set `lifecycle:` to the terminal state and `ended:` to the date the work actually stopped, not
today's date, unless they are the same. For `superseded`, the replacing design carries
`extends: <slug>.md`.

Close the epic if it is still open. Where the initiative had a public collaboration issue, that
closes through its own public flow; `bd close` remains the private close signal.

Completion: the doc carries `lifecycle:` and `ended:`, the epic is closed, and an exact-`spec_id`
filter over `bd list --spec "design:<slug>"` shows nothing open.

### 5. Close

Report per doc: terminal state, ADRs created, `CONTEXT.md` entries added, and any criterion that
went unmet.

## Frontmatter vocabulary

One field set across every Brain: `lifecycle:` (required), `started:` and `ended:` (dates),
`extends:` (a design this one builds on), `residue:` (ADR ids produced, e.g. `[ADR-0038]`).

Per-doc invented fields drift the vocabulary apart and make a sweep impossible to run. Where a doc
needs to say something the set cannot, say it in prose under the relevant section.
