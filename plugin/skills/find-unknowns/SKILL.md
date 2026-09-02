---
name: find-unknowns
description: Scans an unfamiliar codebase or feature area against the project Brain and reports the unknown-unknowns and tacit assumptions that would change the approach. Read-only. Use when entering unfamiliar territory, orienting at the start of an initiative, or before committing to a design or a risky change.
---

# Find Unknowns

Orient before building. The cheapest place to catch an unknown is before implementation, so this
skill scans the territory an initiative touches and reports the gap between the project's map (the
Brain: vocabulary, decisions, rules) and the codebase reality.

The output is a triaged set of unknowns, not a plan and not code. This skill is read-only: it writes
nothing to the Brain. It surfaces unknowns and hands each one to the skill that owns the write.

## The frame

`DOTBRAIN.md` defines the four quadrants of unknowns; use those terms exactly. The Brain already
answers many known knowns, so this skill spends its budget on **unknown knowns** and **unknown
unknowns**: the two no planning step catches, because you do not know to ask.

## Stop before you start

Orienting costs a scan the work may not repay. Skip it, and send the work straight to beads, unless
at least one holds:

- The initiative is unfamiliar territory, or crosses modules.
- It carries meaningful risk.
- You cannot yet state its intended shape in one paragraph.

State the decision — orient or skip — with the reason, before going further.

## Process

### 1. Read the map

Read the nearest `AGENTS.md`, `CONTEXT.md`, relevant `adr/`, and any `.brain/docs/` that bears on the
area. This collapses the known-unknowns the Brain already settles, so the scan does not re-ask
documented questions.

Completion: every question the Brain already settles is named alongside the canon entry that
settles it, so the scan does not re-ask it.

### 2. Scan the territory

Explore the actual modules the initiative touches. Use a fan-out explore tool for broad sweeps if one
is available; otherwise read directly. Stay grounded: a finding must point at a concrete file,
behavior, or dependency, never a generic category.

Completion: the modules, integration points, and dependencies in play are listed, each pointing at
a file you actually read.

### 3. Run the blindspot pass

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

Every finding names a file, behavior, or dependency you actually read. A finding you cannot ground
that way is a generic checklist item ("did you consider error handling?"), which the agent would
have produced anyway: drop it rather than padding the list.

Completion: a triaged list of findings, each grounded in something read and carrying a blast-radius
call, ordered largest-first.

### 4. Hand off

This skill does not write the Brain. Route each finding to the skill that owns it:

- Durable design gap for an initiative: `to-design` (becomes a `Known Unknowns` entry).
- Open question needing a human answer: `grill-decisions`.
- Durable, cross-cutting, expensive-to-reverse decision: an ADR, via `grill-decisions`.
- Concrete follow-up work: a bead, via `operate-execution`.
- If the pass shows the work is actually small and obvious: straight to beads, no design doc.

Completion: every finding has a named next action, and you have recommended the next skill.

