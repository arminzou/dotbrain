---
name: maintain-brain
description: Capture, update, check, and clean up private project understanding. Use when preserving useful context, revising a Brain record, checking drift or broken references, or removing obsolete and redundant Brain material.
---

# Maintain Brain

Keep private project understanding accurate, reachable, and supported by evidence.
These are record operations usable by any workflow. The selected workflow determines
when capture happens and who performs it.

## Authority and destinations

Read the nearest project instructions and the relevant existing records before writing.
Capture information when later work needs understanding that existing sources do not
adequately preserve, or when the user requests it. Session reasoning, easy lookups, and
disposable experiments may stay temporary. Use the project's established vocabulary.
The destinations below apply to material worth retaining; a task need not produce a record.

| Information | Destination | Reference to read for this operation |
| --- | --- | --- |
| Settled domain terms and relationships | `.brain/CONTEXT.md` | [Vocabulary](references/context-format.md) |
| Adopted decisions whose rationale needs independent preservation | `.brain/adr/` | [ADR selection and decisions](references/adr-format.md) |
| Initiative intent, design, uncertainty, and outcome | `.brain/designs/` | [Designs and lifecycle](references/design-format.md) |
| Verified findings, supporting sources, maintained explanations | `.brain/docs/` | [Findings and references](references/findings.md) |
| Work needing durable continuation or coordination, including agreed follow-up | Beads | Use `work-graph` for graph operations |
| Adopted public repository requirements and their routing | Repository `RULES.md` and `AGENTS.md` | Use `repo-rules` for public requirement changes |

Read [Writing for agents](references/writing.md) when authoring agent-consumed prose.
It includes placement guidance and the shared writing discipline.

Recording an observation does not adopt a decision. Distinguish:

- **Observed:** what a named source or check actually establishes, with its applicability.
- **Inferred:** an explanation drawn from evidence, with its reasoning and uncertainty.
- **Hypothesis:** an unresolved possibility and what would test it.
- **Proposed:** a suggested choice or requirement awaiting the applicable authority.
- **Accepted:** a choice adopted by the responsible person or established project authority,
  with the approval source and date.

Within an authorized capture, record needed facts and already approved decisions without
repeated approval. Consequential new choices, contested meaning, and changes to scope,
criteria, or authority require the applicable decision; preserve the unresolved question
and supporting evidence when needed for continuation. Existing criteria remain intact.
Current code proves behavior, not historical intent. Surface conflicts with accepted
decisions rather than silently rewriting them to match implementation.

Retained private evidence and proposed improvements stay in private records or Beads.
`repo-rules` can derive standalone public wording from adopted requirements. A recurring
private preference alone does not establish a repository requirement. Never copy private
paths, identifiers, operational state, or sensitive evidence into public guidance; keep
credentials out of all records.

## Capture or update

Use the destination's reference above. Prefer updating the appropriate existing record
or linking its source over creating a parallel explanation. Keep the source, date or
revision, applicability, and authority beside the claim they support. Link related records
instead of duplicating their rationale. Missing evidence stays a named gap.

Preserve a useful conclusion with enough evidence to assess it. Keep its prototype or raw
artifacts only when reproduction, consequential evidence, review, or unfinished work needs
them. Preserving a conclusion does not require preserving every experimental variant.

Before saving, reread the current target and reconcile concurrent edits. Check numbering
again when creating a numbered record; do not overwrite an existing file. If competing
writes cannot be reconciled safely, preserve both contributions and report the conflict.

Completion: every captured claim has a fitting destination, distinguishable evidence and
authority, and enough provenance for a later reader to assess or retrieve its source.

## Check or clean up private context

For a check request, report findings without editing. For authorized maintenance, inspect
the named records and their inbound and outbound pointers. Look for conflicting meaning,
stale claims, duplicate authorities, misplaced execution state, broken links, weak retrieval
conditions, and private information exposed publicly. Verify suspected drift against
current evidence before changing it.

Within authorized cleanup, remove obsolete, redundant, or misleading material that no
longer supports current understanding or unfinished work. Retain independently useful
rationale and evidence where needed, and repair affected pointers. Historical interest
alone does not require keeping a file; existing version history can provide recovery.
Deletion need not produce a replacement summary.

Preserve unrelated user content and literal examples, active requirements, and existing
work state. User-authored material may be cleaned up when that material is within the
authorized scope. Reading a record does not itself require maintenance; ordinary work
does not trigger a Brain-wide cleanup. Report wiring problems for `wire-brain`; report public
requirement or routing changes for `repo-rules`.

Completion: authorized repairs resolve the supported findings, remaining pointers work,
needed knowledge and unfinished work survive, and out-of-scope changes remain explicit.

## Record lifecycle evidence

Use [Designs and lifecycle](references/design-format.md) for a design's terminal update.
Document state describes initiative history; Beads remains the authority for task state.
A terminal record requires evidence for its claimed outcome and the applicable authority.
It does not itself accept work, close tasks, approve a PR, or authorize delivery.

## Report

Name the records changed or checked, the material captured, and any unresolved decision,
evidence gap, conflict, or proposed follow-up. Distinguish writing a record from verifying
the behavior it describes.
