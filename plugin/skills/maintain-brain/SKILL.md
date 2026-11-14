---
name: maintain-brain
description: Capture and maintain private project vocabulary, decisions, initiative designs, findings, references, and lifecycle evidence. Use when recording project understanding, updating a Brain record, or checking private context for drift, duplication, or broken references.
---

# Maintain Brain

Keep private project understanding accurate, reachable, and supported by evidence.
These are record operations usable by any workflow. The selected workflow determines
when capture happens and who performs it.

## Authority and destinations

Read the nearest project instructions and the relevant existing records before writing.
Use the project's established vocabulary and preserve consequential rationale and evidence.

| Information | Destination | Reference to read for this operation |
| --- | --- | --- |
| Settled domain terms and relationships | `.brain/CONTEXT.md` | [Vocabulary](references/context-format.md) |
| Consequential decisions and rationale | `.brain/adr/` | [Decisions](references/adr-format.md) |
| Initiative intent, design, uncertainty, and outcome | `.brain/designs/` | [Designs and lifecycle](references/design-format.md) |
| Verified findings, supporting sources, maintained explanations | `.brain/docs/` | [Findings and references](references/findings.md) |
| Tasks, dependencies, assignments, acceptance, execution evidence, pending improvements | Beads | Use `work-graph` for graph operations |
| Adopted public repository requirements and their routing | Repository `RULES.md` and `AGENTS.md` | Use `repo-rules` for public requirement changes |

Read [Writing for agents](references/writing.md) when authoring agent-consumed prose.
It includes placement guidance and pointers for VitePress and Mermaid syntax.

Recording an observation does not adopt a decision. Distinguish:

- **Observed:** what a named source or check actually establishes, with its applicability.
- **Inferred:** an explanation drawn from evidence, with its reasoning and uncertainty.
- **Hypothesis:** an unresolved possibility and what would test it.
- **Proposed:** a suggested choice or requirement awaiting the applicable authority.
- **Accepted:** a choice adopted by the responsible person or established project authority,
  with the approval source and date.

Record settled facts and already approved decisions within the authorized scope without
repeated approval. Consequential new choices, contested meaning, and changes to scope,
criteria, or authority require the applicable decision; preserve the unresolved question
and supporting evidence meanwhile. Existing criteria remain intact until that decision.
Current code proves behavior, not historical intent. Surface conflicts with accepted
decisions rather than silently rewriting them to match implementation.

Private evidence and proposed improvements remain in private records or Beads.
`repo-rules` can derive standalone public wording from adopted requirements. A recurring
private preference alone does not establish a repository requirement. Never copy private
paths, identifiers, operational state, or sensitive evidence into public guidance; keep
credentials out of all records.

## Capture or update

Use the destination's reference above. Prefer updating the appropriate existing record
over creating a parallel explanation. Keep the source, date or revision, applicability,
and authority beside the claim they support. Link related records instead of duplicating
their rationale. Missing evidence stays a named gap.

Before saving, reread the current target and reconcile concurrent edits. Check numbering
again when creating a numbered record; do not overwrite an existing file. If competing
writes cannot be reconciled safely, preserve both contributions and report the conflict.

Completion: every captured claim has a fitting destination, distinguishable evidence and
authority, and enough provenance for a later reader to assess or retrieve its source.

## Check or repair private context

For a check request, report findings without editing. For authorized maintenance, inspect
the named records and their inbound and outbound pointers. Look for conflicting meaning,
stale claims, duplicate authorities, misplaced execution state, broken links, weak retrieval
conditions, and private information exposed publicly. Verify suspected drift against
current evidence before changing it.

Move or prune only within the authorized scope. Preserve adopted requirements, user content,
literal examples, consequential rationale, and historical evidence. Update affected pointers
when moving material. Mark superseded claims and their replacements rather than erasing
the reason an earlier decision existed. Existing notebooks remain intact unless their
migration is explicitly in scope. Report wiring problems for `wire-brain`; report public
requirement or routing changes for `repo-rules`.

Completion: authorized repairs resolve the supported findings, moved knowledge stays
reachable, and unresolved conflicts and out-of-scope changes remain explicit.

## Record lifecycle evidence

Use [Designs and lifecycle](references/design-format.md) for a design's terminal update.
Document state describes initiative history; Beads remains the authority for task state.
A terminal record requires evidence for its claimed outcome and the applicable authority.
It does not itself accept work, close tasks, approve a PR, or authorize delivery.

## Report

Name the records changed or checked, the material captured, and any unresolved decision,
evidence gap, conflict, or proposed follow-up. Distinguish writing a record from verifying
the behavior it describes.
