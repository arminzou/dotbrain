# Work intake: bead vs design doc

This reference governs when new work should enter the work graph as a direct bead and when
`manage-work-graph` should suggest a design doc plus epic workflow.

## Direct bead

Work can enter as a direct bead, without a design doc, when all of the following are true:

- it is a single unit of work, not a multi-item initiative
- the design is obvious enough that a separate design narrative would add little value
- it does not cross multiple systems, workflows, or operator-facing contracts
- it does not carry meaningful open questions, phased rollout, or major alternatives

Typical examples:

- a narrow bug fix
- a small refactor inside one module boundary
- a maintenance chore with no meaningful design ambiguity

## Suggest a design doc plus epic

Suggest the `to-design` -> `to-issues` workflow when any of the following are true:

- the work is multi-step or will likely decompose into multiple dependent work items
- the work crosses modules, workflows, or user/operator-facing contracts
- the work has meaningful open questions, competing approaches, or explicit non-goals
- the work needs phased rollout or a human-readable design trail during execution
- the work needs a living place to track design-level discoveries and unknowns as implementation
  changes the initiative story

When suggesting this path, be explicit: "This looks like design-doc work rather than a direct bead
- want me to run `to-design` and formalize it?" Do not force the workflow; offer it.

## Discovery rule during execution

Once an initiative is design-linked:

- the active design doc owns the design, known unknowns, design-level discoveries, and
  deviations
- beads own status, dependencies, acceptance, ownership, and closure
- design-linked work items should link back with `--spec-id design:<slug>` instead of copying the
  initiative design into bead `--design`

The lead records verified discoveries, resolved unknowns, and outcomes without routine approval.
Update the active design when they change the initiative story; keep item-local execution detail
in the bead. Delegated workers return findings and evidence in their item comments; they do not
gain permission to edit the graph or active design.

Keep the observation and its evidence, the revision/environment where it applies, and any inference
or unresolved hypothesis distinguishable. Resolve an unknown only to the extent the evidence
settles it; retain remaining uncertainty and its next action. Record proposals as proposals,
including the decision still needed. Observed behavior does not replace an accepted decision.
New consequential product/architecture decisions and scope, criteria, or authority changes retain
their human gates; reuse applicable approval without asking again.

Durable vocabulary belongs in `CONTEXT.md`, accepted decision rationale in ADRs through
`grill-decisions`, and derived explanations or runbooks in `.brain/docs/`. Use those existing
owners and formats when the finding belongs beyond the initiative; do not copy execution state
into them. Context curation keeps its Check/Fix authority boundary. Transferable practices remain
retro candidates in work records under `run-execution`; only `run-retro` writes `RETRO.md`.
