# designs/

Design docs - one initiative per file.

An `active` design doc is a living unknowns ledger for the initiative. It should capture the
current design, known unknowns, design-relevant implementation discoveries, deviations, and any
human design calls still needed. Author only the sections the initiative needs.

Typical sections include motivation, goals, non-goals, current design, known unknowns,
implementation notes, deviations, human decisions needed, alternatives considered, and rollout.

Authored by the `to-design` skill, then decomposed into a bead epic by `to-issues`. Beads own
execution state, dependencies, claim status, and acceptance criteria. When a design reaches
`shipped`, `abandoned`, or `superseded`, it freezes as a point-in-time record. Durable residue
lands in `adr/` (decisions) and `CONTEXT.md` (vocabulary); a maintained "how it works now"
description is a `docs/` runbook. On conflict with canon, canon wins.

See `DOTBRAIN.md` for the read order and operating rules.
