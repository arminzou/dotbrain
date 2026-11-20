# designs/

Design docs - one initiative per file.

An `active` design doc is a living unknowns ledger for the initiative. It should capture the
current design, verification / success criteria, known unknowns, design-relevant implementation
discoveries, deviations, and any
human design calls still needed. Author only the sections the initiative needs.
Label unresolved choices beside the relevant text; an `active` design does not
make every option within it an accepted decision.

Use `lifecycle:` frontmatter to mark document mutability: `draft`, `active`, `shipped`,
`abandoned`, or `superseded`. This is not execution status; beads own execution state.

Once a design is `active`, criteria changes are human decisions: record them in the doc
(`Deviations` or `Human Decisions Needed`), not silently edited in place. When a design ships,
record the verification evidence achieved, so a later reader can check the gate still catches the
failure it was written for (gates rot).

Typical sections include motivation, goals, non-goals, current design, verification / success
criteria, known unknowns, implementation notes, deviations, human decisions needed, alternatives
considered, and rollout.

Maintain these records through `maintain-brain`. Beads own
execution state, dependencies, claim status, and acceptance criteria. When a design reaches
`shipped`, `abandoned`, or `superseded`, it freezes as a point-in-time record.
Extract only adopted decisions that meet the ADR criteria and need independent discovery;
link existing ADRs rather than duplicating them. Other choices can stay in the historical
design. Lasting vocabulary belongs in `CONTEXT.md`; a maintained "how it works now"
description is a `docs/` runbook. Resolve conflicts against applicable adopted guidance,
including amendments; a document's location alone does not make a claim current or binding.

See `DOTBRAIN.md` for record meanings and private/public boundaries.
