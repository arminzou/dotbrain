# Work intake: bead vs design doc

This reference governs when new work should enter the execution graph as a direct bead and when
`operate-execution` should suggest a design doc plus epic workflow.

## Direct bead

Work can enter as a direct bead, without a design doc, when all of the following are true:

- it is a single unit of work, not a multi-slice initiative
- the design is obvious enough that a separate design narrative would add little value
- it does not cross multiple systems, workflows, or operator-facing contracts
- it does not carry meaningful open questions, phased rollout, or major alternatives

Typical examples:

- a narrow bug fix
- a small refactor inside one module boundary
- a maintenance chore with no meaningful design ambiguity

## Suggest a design doc plus epic

Suggest the `to-design` -> `to-issues` workflow when any of the following are true:

- the work is multi-step or will likely decompose into multiple dependent slices
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
- design-linked slices should link back with `--spec-id design:<slug>` instead of copying the
  initiative design into bead `--design`

If implementation reveals something that changes the design story, update the active design doc. If
the discovery is only slice-local execution detail, keep it in the bead.
