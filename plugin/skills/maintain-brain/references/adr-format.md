# Decisions

ADRs live in `.brain/adr/` as `NNNN-slug.md`. Create the directory only when needed.
For a new record, inspect the highest existing prefix and increment it, starting at
`0001`. Recheck immediately before creation to avoid a concurrent numbering collision.

Use an ADR for a choice that is costly to reverse, surprising without context, and the
result of a real tradeoff. Smaller choices may stay in the relevant design or explanation.
Accepted decisions and consequential rejected alternatives both deserve preserved rationale.

```md
---
status: proposed
date: YYYY-MM-DD
---

# Decision title

Context, the proposed or adopted choice, and why it fits. State the alternatives and
consequences that a future reader would otherwise miss.

Authority: who adopted the choice, when, and where that approval is recorded; or explicitly
state that adoption is pending.

Evidence: source links, revisions, observations, and limits supporting the rationale.
```

Use `status: accepted` only with the applicable approval or established authority.
`deprecated` and `superseded` describe later changes; name and link the replacing record
when one exists. Existing records need no wholesale reformatting to add missing provenance.
A paragraph can be enough when it carries the choice, rationale, authority, and evidence.

Implementation that conflicts with an accepted ADR is a discrepancy to record and resolve,
not proof that the ADR was revoked. Preserve the old rationale when amending or superseding
a choice, and link the records in both directions. Link from designs to the ADR instead
of maintaining another copy of its rationale.
