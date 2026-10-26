---
name: close-design
description: Closes a shipped, abandoned or superseded design — checks shipment evidence, promotes durable residue, stamps frontmatter and closes the epic. Use when the human asks to close out, wrap up or finish a design.
---

# Close Design

A design doc is `active` only while it is the living design authority. Once the work lands, is
dropped, or is replaced, the doc freezes and its durable residue belongs in canon. This skill owns
that transition.

Run it only when the human asks for closeout, by name or in words, including sweep and retroactive cases.
Closing implementation or review work and delivering a ready PR never invokes it on its own.
The design and epic remain active until the human asks for terminal closeout. Do not poll for merge.

## Stop before you start

- The initiative is still live — a doc with open work items under its epic is `active` by definition,
  and freezing it strands the work. Only the sweep case below reads a still-`active` doc.
- You are here to close a bead, not a doc. Closing the epic is the last act of this transition,
  never a way to manage work.

## Branches

| Trigger | Terminal state |
|---|---|
| Actual PR merged into the agreed target and verification evidence recorded | `shipped` |
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
drawing any conclusion about which work items belong to this doc. `--spec-id` is a `bd create` flag and
is not accepted by `bd list`.

For a sweep, enumerate every doc in `.brain/designs/` with its lifecycle and the state of its epic.
Closed work items alone do not establish shipment. For shipped work, inspect the actual PR's
repository, delivery branch, target branch, merged state, merge commit and merge date; record its
URL and merge evidence. A closed-unmerged PR never establishes shipment. A ready or approved PR
is still awaiting human merge, so leave the design and epic active. If PR state is unavailable or
does not match the agreed delivery, report the gap and stop shipped closeout.
For a sweep, apply the same evidence check to each candidate. An explicitly dropped initiative
is abandoned; a replaced design is superseded and names its replacement. Neither classification
is inferred merely from PR closure; each needs its own supporting evidence.

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
- **A retro candidate** — a practice from the overall approach or goal outcomes that would change
  another initiative's decisions. Record it as a `## Retro candidate` comment on the epic before
  closing it, and flag the epic with `bd update <epic> --set-metadata dotbrain_retro=candidate`;
  `run-retro` curates it into `RETRO.md`. Reuse candidates and findings already recorded at task
  closure rather than recording them again. Never write `RETRO.md` here.
- **Nowhere** — item-local facts that die with their beads.

Write the ADR ids you created into the doc's `residue:` frontmatter, so provenance survives in both
directions.

Completion: every entry under `Known Unknowns`, `Deviations`, and `Implementation Notes` has
been placed in one of these destinations, and `residue:` lists every ADR the initiative produced.

### 4. Stamp and close

Set `lifecycle:` to the terminal state and `ended:` to the date the work actually stopped, not
today's date, unless they are the same. For `superseded`, the replacing design carries
`extends: <slug>.md`.

Close the epic if it is still open. Implementation and review records may already have closed
under their own acceptance rules before PR approval or merge; that grants no shipment authority.
For any surviving review bead, follow the review closing rules: required verdict and evidence,
resolved blocking findings, and recorded dispositions. Unresolved findings remain explicit;
terminal closeout never bypasses their gates or hides them under a shipped design.

Where the initiative had a public collaboration issue, that closes through its own public flow;
`bd close` remains the private close signal.

Completion: the doc carries `lifecycle:` and `ended:`, the epic is closed, and an exact-`spec_id`
filter over `bd list --spec "design:<slug>"` shows nothing open except any review bead left as a
surviving gate.

### 5. Close

Report per doc: terminal state, ADRs created, `CONTEXT.md` entries added, and any criterion that
went unmet.

## Frontmatter vocabulary

One field set across every Brain: `lifecycle:` (required), `started:` and `ended:` (dates),
`extends:` (a design this one builds on), `residue:` (ADR ids produced, e.g. `[ADR-NNNN]`).

Per-doc invented fields drift the vocabulary apart and make a sweep impossible to run. Where a doc
needs to say something the set cannot, say it in prose under the relevant section.
