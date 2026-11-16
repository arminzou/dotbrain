# Designs and lifecycle

A design preserves an initiative's intent, interfaces, constraints, uncertainty, and
verification outcomes. Durable execution state stays in Beads. Use a design when the
initiative needs this continuing explanation; the format does not require creating a
document for every task or opening an epic as a side effect of writing one.

Designs live in `.brain/designs/NNNN-slug.md`. Inspect the highest prefix and increment it
for a new document (`0001` when empty); recheck before creation for concurrent writers.
Use established vocabulary and link consequential decisions to their ADRs.

## Record structure

Keep only sections the initiative needs. Existing content and adopted criteria survive
maintenance; this outline is an authoring aid, not a migration requirement.

```md
---
lifecycle: draft
started: YYYY-MM-DD
---

# Initiative title

## Motivation

The problem and why it matters.

## Goals and scope

Intended outcomes, constraints, and explicit exclusions.

## Design

The intended behavior, interfaces, integration points, and relevant resource prerequisites.

## Success Criteria

The adopted outcomes and how each is assessed, including what each check leaves unproven.
Identify proposed criteria as pending until adopted.

## Verification Evidence

Actual outcomes for each criterion, with revision, environment, date, and evidence locations.

## Known Unknowns

Open questions, their evidence, what would resolve them, and whether they block the design
or are explicitly deferred with a reason.

## Deviations

What changed and why, with the authority and before/after meaning for approved scope or
criteria changes.
```

Add implementation constraints, alternatives, rollout, or unresolved human decisions when
they clarify the initiative. Record applicable authorization and limits as facts when
needed; authoring the document grants no execution or delivery authority. Keep task lists,
assignments, attempts, and acceptance status in Beads and link them for evidence.

## Lifecycle semantics

Use `lifecycle` with `draft`, `active`, `shipped`, `abandoned`, or `superseded`.
`draft` is a proposed initiative; `active` is the current living initiative design.
The applicable user or project authority determines adoption and terminal transitions.
Reuse already recorded approval; missing authority remains explicit.

Use `started` and `ended` for dates, `extends` for a design this one builds on, and
`residue` for decision records produced. Use the existing project's value representation
and preserve its links. Describe additional details in prose rather than inventing a
parallel lifecycle vocabulary.

| Terminal state | Evidence needed |
| --- | --- |
| `shipped` | Actual delivery to the agreed destination and the verification outcomes; inspect the delivery artifact or state rather than inferring shipment from closed tasks |
| `abandoned` | The decision to stop without delivering the initiative, its authority, and what was learned |
| `superseded` | The replacement design and the authority or event establishing replacement |

If delivery requires a merged PR, verify the actual repository, target, merge revision,
date, and URL. A ready, approved, or closed-unmerged PR proves no merge. Other delivery
arrangements use their own agreed evidence. Record evidence gaps rather than inventing
success or adding a new delivery requirement.

Before a terminal update, reconcile linked work and unresolved findings. Open work remains
visible in Beads with its disposition; freezing a design must not hide it or imply its
acceptance. If querying by a design identifier, check exact identity: tracker prefix matches
may include another initiative. Task closure is a separate graph operation under its
applicable authority.

Record one verification outcome per success criterion: passed, failed, dropped by an
authorized change, or never run. Preserve `Success Criteria`; record unmet outcomes plainly
in `Verification Evidence`. Criteria changes require their own authority and deviation
record, not a rewrite to fit the result. Include the revision and environment so evidence
does not become a timeless guarantee.

Promote lasting vocabulary to `CONTEXT.md`, decisions to `adr/`, and maintained findings
or explanations to `docs/`, with backlinks for provenance. Pending improvements belong in
Beads. Keep item-local evidence in its existing work record. Preserve existing notebooks
and historical evidence; lifecycle recording imposes no retrospective notebook process.

Set `ended` to when the initiative actually ended, naming uncertainty if the date is
unknown. A terminal design is a historical record: later corrections retain the original
outcome and explain the correction. A replacement can name its predecessor in `extends`.
