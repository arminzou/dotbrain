# Decisions

ADRs live in `.brain/adr/` as `NNNN-slug.md`. Create the directory only when needed.
For a new record, inspect the highest existing prefix and increment it, starting at
`0001`. Recheck immediately before creation to avoid a concurrent numbering collision.

Ask: what would a future reader get wrong with the code and current docs, but without
the reason for this choice? Does that understanding need an independently discoverable
record, or can it be reliably recovered from existing sources when needed?

- Keep unresolved options in the relevant design or findings record until adopted.
- Keep routine, readily reconstructable choices in their existing explanation.
- Write a short ADR when losing the rationale could cause a concrete, consequential
  mistake: repeating a failed approach, violating an external commitment, or removing a
  deliberate constraint. Support that consequence with evidence or an adopted commitment;
  code-change difficulty alone does not determine its importance.
- If a design, commit, PR, or discussion already preserves the rationale and future
  readers can reliably find and access it, leave it there. Extract a short ADR when
  consequential rationale would otherwise be repeatedly reconstructed or easily lost;
  link its evidence instead of copying the source history.

Use relevant existing pointers to assess recoverability; no exhaustive history search is
required for every choice. Code and executable checks establish behavior; a feature map,
when present, locates capabilities and verification paths. Historical evidence supplies
reasons. Recalled conversations can recover recent work and unfinished thinking; retain
their uncertainty and distinguish proposals from adopted choices. A source that is
inaccessible, hard to find, or never captured is not reliable recovery.

When the user asks for an ADR, assess whether a separate record earns its cost. If the
choice is unresolved, routine, or already adequately recorded, briefly explain why and
recommend the existing design or explanation as its home. Offer that judgment once; if
the user still wants an ADR, write it. An explicitly requested draft uses `status: proposed`
and states that it establishes no implementation constraint.

Use this outline for an adopted choice:

```md
---
status: accepted
date: YYYY-MM-DD
---

# Decision title

Context, the adopted choice, and why it fits. State the alternatives and
consequences that a future reader would otherwise miss.

Authority: who adopted this choice and scope, when, and where that approval is recorded.

Evidence: source links, revisions, observations, and limits supporting the rationale.
```

Use `status: accepted` only with the applicable approval or established authority.
Reuse existing authority; acceptance covers the identified choice and scope, not every
option discussed. Implementation and verification are separate facts.
`deprecated` and `superseded` describe later changes; name and link the replacing record
when one exists. Existing records need no wholesale reformatting to add missing provenance.
A paragraph can be enough when it carries the choice, rationale, authority, and evidence.
For example: "We chose X over Y because Z. Reconsider when W changes." Include a
reconsideration condition when known; do not invent one to fill the outline.

Implementation that conflicts with an accepted ADR is a discrepancy to record and resolve,
not proof that the ADR was revoked. Preserve the old rationale when amending or superseding
a choice, and link the records in both directions. Put the current disposition and amendment
or replacement pointer near the opening; identify which claims changed and which still
apply. Update when a relevant choice changes or a conflict is encountered, without periodic
rewrites or a documentation step for every code change. Link from designs to the ADR
instead of maintaining another copy of its rationale.
