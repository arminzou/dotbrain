# Writing within dotbrain

The principles in [Writing for agents](writing.md) apply across visibility surfaces.
Placement and authority differ:

| Surface | Typical documents | Constraint |
| --- | --- | --- |
| Public repository | `AGENTS.md`, `RULES.md`, README, architecture and contributor docs | Useful without private access; contains no private Brain material |
| Private project Brain | `CONTEXT.md`, ADRs, designs, findings, references, explanations | Preserves project understanding, rationale, evidence, and applicability |
| User data root | Selected skills and their references | Follows the nearest authoring policy; placement alone does not activate a skill |

Public `AGENTS.md` routes to repository requirements in `RULES.md` and task-specific
references. `repo-rules` maintains those requirements and their routing. Public rationale
must stand on its own: express necessary reasoning without private paths, identifiers,
or operational state. Keep private sources and provenance in private records.

`maintain-brain` provides [vocabulary](context-format.md), [decision](adr-format.md),
[design and lifecycle](design-format.md), and [finding/reference](findings.md) semantics.
These formats describe records, evidence, and authority. A chosen workflow supplies
capture timing, writing responsibility, review, and delivery procedures. Beads owns
durable execution state; a design or explanatory document must not become a second
task tracker.

## Shapes for agent instructions

Choose structure according to the document's actual job:

| Shape | Useful structure |
| --- | --- |
| Linear procedure | Prerequisites above ordered steps; completion criteria for each non-terminal step |
| Loop | Repeatable protocol with a clear exit condition |
| Reference | Definitions, rules, examples, and conditional retrieval pointers |
| Tool driver | Branch selector, symptom-to-command guidance, and verification |

Name a terminal action for what it does: report findings, hand off an unresolved action,
or complete a record update. Add a separate terminal section only when it clarifies the
outcome. Keep conditions beside the actions they constrain.
