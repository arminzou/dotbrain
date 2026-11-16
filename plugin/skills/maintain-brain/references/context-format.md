# Vocabulary

Settled project vocabulary lives in `.brain/CONTEXT.md`. Read it before adding or
changing a term. Include domain concepts, their boundaries, aliases, and relationships;
general programming concepts and implementation instructions belong elsewhere.

Use the existing layout. A small context can use this form:

```md
# Project context

One or two sentences describing the domain.

## Language

**Initiative**: A bounded effort with a stated outcome.
_Avoid_: Project, when referring to an effort within this project.

**Decision**: An adopted choice with recorded rationale.

## Relationships

- An **Initiative** may produce several **Decisions**.

## Flagged ambiguities

- A proposed term remains unresolved; record the competing meanings and their sources.
```

Keep definitions concise and use canonical terms consistently. Group terms when distinct
domain areas need it; use relationships and a short example when they clarify boundaries.
Record the source of an adopted definition or link its decision rationale. An unresolved
term stays explicitly unresolved; do not choose an interpretation merely to tidy the file.

Changing a settled definition may change project meaning. Retain the earlier meaning and
its rationale through the appropriate decision record when the change is consequential.
