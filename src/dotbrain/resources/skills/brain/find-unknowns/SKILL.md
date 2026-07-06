---
name: find-unknowns
description: Surface blind spots and unknowns before implementing. Scan an unfamiliar codebase or feature area against the project Brain, then report the unknown-unknowns and tacit assumptions that would change the approach. Use when entering unfamiliar territory, orienting at the start of an initiative, or before committing to a design or a risky change.
---

# Find Unknowns

Orient before building. The cheapest place to catch an unknown is before implementation, so this
skill scans the territory an initiative touches and reports the gap between the project's map (the
Brain: vocabulary, decisions, rules) and the codebase reality.

The output is a triaged set of unknowns, not a plan and not code. This skill is read-only: it writes
nothing to the Brain. It surfaces unknowns and hands each one to the skill that owns the write.

## The frame

Four quadrants of what an initiative knows about itself:

- **Known knowns**: stated goal, constraints, intended shape. Already in the prompt or the Brain.
- **Known unknowns**: questions you know are open.
- **Unknown knowns**: tacit preferences or domain expectations a human recognizes only when shown.
- **Unknown unknowns**: constraints, edge cases, existing behavior, or better approaches you have not
  thought to consider.

The Brain already answers many known knowns. This skill spends its budget on the last two quadrants,
the ones no planning step catches because you do not know to ask.

## Process

### 1. Decide whether to orient

Skip small, obvious, well-scoped work; send it straight to beads. Orient when the initiative is
unfamiliar, crosses modules, carries meaningful risk, or you cannot yet state its intended shape in
one paragraph.

Completion: a one-line decision, orient or skip, with the reason.

### 2. Read the map

Read the nearest `AGENTS.md`, `CONTEXT.md`, relevant `adr/`, and any `.brain/docs/` that bears on the
area. This collapses the known-unknowns the Brain already settles, so the scan does not re-ask
documented questions.

Completion: you can state, in a sentence or two, what the Brain already decides about this area.

### 3. Scan the territory

Explore the actual modules the initiative touches. Use a fan-out explore tool for broad sweeps if one
is available; otherwise read directly. Stay grounded: a finding must point at a concrete file,
behavior, or dependency, never a generic category.

Completion: you can name the specific modules, integration points, and dependencies in play.

### 4. Run the blindspot pass

Now look for what you did not think to ask. Deliberately hunt unknown-unknowns and unknown-knowns:

- Existing behavior that contradicts the intended approach.
- Edge cases, failure modes, and data shapes the plan does not mention.
- Dependencies, invariants, or ordering constraints the codebase enforces silently.
- Decisions that hinge on unstated human preference (unknown knowns): flag them as "you will know it
  when you see it."
- Places where a different approach may be cheaper or safer than the assumed one.

For each finding, capture three things: what it is, why it matters, and its blast radius (would this
change the architecture, the contract, or just an implementation detail?).

Present the findings sorted by blast radius, largest first. The architecture-changing unknowns are the
expensive ones to discover late.

Completion: a triaged list of findings, each with a blast-radius call, ordered largest-first.

### 5. Hand off

This skill does not write the Brain. Route each finding to the skill that owns it:

- Durable design gap for an initiative: `to-design` (becomes a `Known Unknowns` entry).
- Open question needing a human answer: `grill-decisions`.
- Durable, cross-cutting, expensive-to-reverse decision: an ADR, via `grill-decisions`.
- Concrete follow-up work: a bead, via `operate-execution`.
- If the pass shows the work is actually small and obvious: straight to beads, no design doc.

Completion: every finding has a named next action, and you have recommended the next skill.

## Boundaries

- **vs `grill-decisions`**: this skill surfaces what you did not know to ask; grill-decisions resolves
  known questions through back-and-forth. Scanner, then resolver.
- **vs `to-design`**: this runs before you commit to a design doc and feeds its `Known Unknowns`. It
  does not author the doc.
- **vs `review-architecture`**: that assumes you understand the domain and hunts structural depth
  problems; this assumes you do not yet understand and hunts comprehension gaps.

Pipeline position: `find-unknowns` (surface), then `grill-decisions` (resolve), then `to-design`
(capture), then `to-issues` (decompose), then `operate-execution` (build).

## Pitfalls

- **Do not emit a generic checklist.** "Did you consider error handling?" is a no-op. Every finding
  must be grounded in a specific file, behavior, or dependency you actually read. If you cannot ground
  it, drop it.
- **Do not write the Brain.** Surface and hand off; the owning skill writes.
- **Do not resolve the unknowns here.** Surfacing is the job. Resolution is `grill-decisions`, a
  prototype, or a human.
- **Do not over-orient small work.** If the shape is obvious, say so and skip to beads.
