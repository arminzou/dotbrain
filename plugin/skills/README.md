# Dotbrain skills

The plugin ships five workflow-independent capabilities. It needs no private skill
library or engineering workflow installation.

| Skill | Capability |
| --- | --- |
| [wire-brain](wire-brain/SKILL.md) | Provision, attach, inspect, and repair Brainspace wiring and selected resources |
| [brain-convention](brain-convention/SKILL.md) | Explain shared workspace ownership, records, and privacy |
| [maintain-brain](maintain-brain/SKILL.md) | Capture and maintain private project understanding |
| [work-graph](work-graph/SKILL.md) | Inspect and maintain native Beads work records |
| [repo-rules](repo-rules/SKILL.md) | Initialize and reconcile adopted repository requirements |

All five allow model invocation for their stated operations. Engineering
planning, execution, review, and delivery belong to the selected workflow.
The session-start hook delivers the shared convention; `brain-convention` also
provides it on demand. Shared [writing guidance](maintain-brain/references/writing.md)
and syntax references live under `maintain-brain`.

Operator-selected custom skills and agents retain global and project delivery.
Selection lives in `config.yaml` and `project.yaml`; directory membership alone
does not activate a resource. See [upgrade guidance](../../docs/upgrading.md).
