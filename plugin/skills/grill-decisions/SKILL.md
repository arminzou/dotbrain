---
name: grill-decisions
description: Grilling session that challenges a plan against the existing domain model, sharpens terminology, and writes decisions into CONTEXT.md and ADRs inline as they crystallise. Use when the user wants to stress-test a plan against their project's language and documented decisions, or arrives from find-unknowns with open questions to resolve.
---

# Grill Decisions

Interview the user relentlessly about a plan until every branch of the decision tree is resolved.
Challenge it against the project's existing domain language and recorded decisions, and write what
settles into canon as it settles.

## Boundaries

- **vs `find-unknowns`**: that surfaces what you did not know to ask; this resolves questions
  already named. Scanner, then resolver.
- **vs `to-design`**: that captures the settled shape as a design doc; this settles it. Grill first,
  then formalize.
- **vs `review-architecture`**: that grills a structural candidate in architecture vocabulary; this
  grills a plan against domain vocabulary.

Pipeline position: `find-unknowns` (surface), then `grill-decisions` (resolve), then `to-design`
(capture), then `to-issues` (decompose).

## Process

### 1. Read the map

Read `.brain/CONTEXT.md`, the ADRs bearing on the area, and the nearest `AGENTS.md`. Absent or empty
canon is a legitimate state: note the gap and grill anyway.

Completion: you can state the project's existing term for every concept the plan touches, and every
ADR the plan interacts with.

### 2. Lay out the decision tree

Before asking anything, present the branches you intend to walk, in the order you intend to walk
them. Order by dependency: a branch whose answer constrains other branches goes first.

Showing the tree is what makes the session finishable. It gives the user a progress signal, lets
them add a branch you missed, and lets them cut one they consider settled.

Completion: the user has seen the branch list and agreed it is the right shape.

### 3. Walk the branches

Ask one question at a time and wait for the answer before the next one. For each question, give
your recommended answer, so agreeing is cheap and disagreeing is specific.

If a question can be answered by reading the codebase, read the codebase instead of asking. The
user's attention is the scarce resource in this skill.

Four moves carry the grilling:

- **Challenge against the glossary.** When a term conflicts with `CONTEXT.md`, say so immediately:
  "Your glossary defines 'cancellation' as X, but you seem to mean Y. Which is it?"
- **Sharpen fuzzy language.** When a term is vague or overloaded, propose a precise canonical one:
  "You're saying 'account'. Do you mean the Customer or the User? Those are different things."
- **Discuss concrete scenarios.** Invent scenarios that probe edge cases and force precision about
  where one concept ends and the next begins.
- **Cross-reference with code.** When the user states how something works, check whether the code
  agrees, and surface contradictions: "Your code cancels entire Orders, but you just said partial
  cancellation is possible. Which is right?"

Answers spawn new branches; add them to the tree rather than following them immediately and losing
your place. A branch the user declines to settle is deferred with a reason, not silently dropped.

Completion: every branch on the tree is resolved or explicitly deferred with a reason, and the tree
has no branch you added but never returned to.

### 4. Close

Report what the session produced: branches resolved, branches deferred and why, terms added or
sharpened in `CONTEXT.md`, and ADRs written. Recommend `to-design` when the resolved shape is a
multi-step initiative.

## Inline canon updates

Canon is written during the walk, not batched at the end. A term resolved in question three is
written before question four, because a session that ends early still leaves the project better off.

- **Terminology** goes into `CONTEXT.md` the moment it resolves, using
  [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md). Keep it to terms meaningful to a domain expert; leave
  implementation detail out.
- **Decisions** become ADRs only when they pass the three-part test in
  [ADR-FORMAT.md](./ADR-FORMAT.md), which also owns the format and numbering. That test is the
  single source for when any skill offers an ADR.
