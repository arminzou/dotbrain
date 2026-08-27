# Out-of-scope knowledge base

`.out-of-scope/` in the **public code repo** stores public-safe records of rejected enhancement
requests. It is the public derivation of a scope decision whose full reasoning may live privately
(a CONTEXT.md "Avoid" note or an ADR). It serves two purposes:

1. **Institutional memory** — why a feature was rejected, so the reasoning survives the closed issue.
2. **Deduplication** — when a matching request arrives, surface the prior decision instead of
   re-litigating it.

One file per **concept** (`dark-mode.md`, `plugin-system.md`), not per issue. Multiple issues for
the same thing are grouped under one file. Use a short kebab-case concept name.

## File format

Write it like a short design note, not a database row: a `# Concept` heading, why it is out of
scope (referencing project scope, a technical constraint, or a strategic choice — durable reasons,
not "too busy right now"), and a **Prior requests** list of issue links.

```markdown
# Dark Mode

This project does not support user-facing theming. The rendering pipeline assumes a single palette
resolved at build time; runtime theming is a downstream concern for consumers who embed the output.

## Prior requests
- #42 — "Add dark mode support"
- #87 — "Night theme for accessibility"
```

## When to read

During intake (gather context), scan `.out-of-scope/`. Match by concept similarity, not keywords —
"night theme" matches `dark-mode.md`. On a match, surface it: "This matches `.out-of-scope/dark-mode.md`,
rejected before because [reason]. Still the same call?" The maintainer may **confirm** (append the
issue to Prior requests, close), **reconsider** (delete/update the file, proceed with triage), or
**disagree** (related but distinct, proceed).

## When to write

Only when an **enhancement** (not a bug) is rejected as `wontfix`: create or update the concept
file, post a comment linking it, then close. Bugs are never recorded here.
