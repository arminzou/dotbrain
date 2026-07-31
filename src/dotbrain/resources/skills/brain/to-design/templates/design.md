---
lifecycle: draft
started: <YYYY-MM-DD>
---

# <Initiative title>

<!--
Author only the sections this initiative needs; delete the rest along with their hints.
Keep every section at the interface and behavior level — exact file paths and code snippets go
stale. `DOTBRAIN.md` carries the lifecycle rules that govern this doc over its whole life.

Frontmatter vocabulary: `lifecycle:` (required), `started:` and `ended:` (dates), `extends:` (a
design this one builds on), `residue:` (ADR ids this doc produced, e.g. `[ADR-0038]`). Do not
invent per-doc fields.

Lifecycle: born `draft`. Flip to `active` when the epic exists and execution can start — from then
on this doc is the living design authority, and criteria changes are human decisions recorded under
`Deviations` or `Human Decisions Needed`.

Reaching a terminal state is `close-design`'s job: it records the verification evidence actually
achieved under `Verification Evidence`, so a later reader can check the gate still catches the
failure it was written for (gates rot), then promotes durable residue — decisions to
`adr/`, vocabulary to `CONTEXT.md` — because this doc freezes as a point-in-time record.
-->

## Motivation

<!-- The problem and why it is worth solving now. What breaks or stays impossible without this. -->

## Goals

<!-- What this initiative must achieve, as outcomes rather than tasks. -->

## Non-goals

<!-- Explicitly out of scope. This is what stops the epic sprawling during decomposition. -->

## Design

<!--
The design being built: the system as it will work once this initiative lands, written in present
tense. Not the existing system, which belongs in `Motivation`. This section is rewritten in place
as unknowns resolve, so it always states the latest design rather than the original one.

Ordered by volatility: lead with the decisions most likely to change — data models, type
interfaces, migration shape, UX flows — and put mechanical or obvious work last. Surfacing the
volatile decisions first is what lets a reviewer catch a wrong turn cheaply.

Use one subsection per coherent piece of the design; `to-issues` echoes these headings in slice
titles, so a later reader can match a bead back to its exact section by title alone.
-->

## Success Criteria

<!--
How completion gets proven, written at authoring time. Prefer mechanical pass/fail checks —
concrete commands, tests, screenshots, metrics. Where no automated verifier exists, state the
judgment criterion explicitly as a human decision gate rather than dressing it up as mechanical.

These are human-owned, which makes them changeable but not silently. A criterion that turns out to
be wrong, ambiguous, or unmeetable gets raised under `Human Decisions Needed` with what it should
become and why; once the human approves, the new wording lands here and the before/after goes under
`Deviations`. What is ruled out is an agent relaxing a criterion on its own to match what the build
happens to do.
-->

## Verification Evidence

<!--
Left empty at authoring time; `close-design` fills it in at the terminal transition.

One entry per criterion above, recording what was actually run and what it returned — passed,
failed, dropped, or never run. Keeping the outcome beside the criterion it answers is what lets a
later reader check the gate still catches the failure it was written for (gates rot).
-->

## Known Unknowns

<!--
Open questions that could change the design, each with what would resolve it. An empty section
here means the unknowns were surfaced and none remain — not that nobody looked. Unknowns found
during implementation land here too.
-->

## Implementation Notes

<!-- Constraints and sequencing that shape how slices get built, without being the slices. -->

## Deviations

<!-- Where the built thing diverged from this design, and why. Added during implementation. -->

## Human Decisions Needed

<!-- Calls that are the human's to make, including any criteria change proposed mid-flight. -->

## Alternatives Considered

<!-- Options rejected and the reason. If a rejection is durable and expensive to reverse, it
belongs in an ADR instead — link it from here rather than restating the rationale. -->

## Rollout

<!-- How this reaches users: sequencing, migration, flags, and what happens if it goes wrong. -->
