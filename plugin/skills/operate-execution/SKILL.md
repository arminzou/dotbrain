---
name: operate-execution
description: Creates, claims, works on, and closes issues in the project's private execution graph. Use for any interaction with the project issue tracker — filing work items, claiming tasks, inspecting the ready frontier, updating status, closing completed work. NOT for decomposing a design doc into an epic (to-issues), formalizing an initiative (to-design), closing one out (close-design), or triaging public issues (triage-public).
---

# Operate Execution

Operate the Brainspace's private execution layer: a typed, prioritized **dependency graph** of
work items. The engine is declared in `project.yaml` (`execution-engine:`) and is beads in practice:
this skill and the design-lifecycle skills use `bd` directly. This file owns the model and workflow;
[references/beads.md](references/beads.md) owns how to express work in beads' native fields.

The dependency graph is the concurrency contract: the **ready frontier** (open items with no open
blockers) is the set safe to claim and run in parallel; blocking edges are the serialization. There
is no separate coordination mechanism.

- **Private execution graph** — work items in the engine's store; this skill owns it and it is the
  source of truth. Never mirror work state into markdown docs, ROADMAPs, TodoWrite/task lists, or
  a public issue tracker.
- **Public issue tracker** — handled by `triage-public`; existing public collaboration may be
  promoted inward with a provenance link, but private work is never published outward for tracking.
  See [references/public-provenance.md](references/public-provenance.md) when work crosses that
  boundary.
- **Knowledge layer** — `.brain/CONTEXT.md`, `.brain/adr/`, `.brain/AGENTS.md`; owned by other skills.

## What this skill owns

- shape epics, tasks, dependencies, and acceptance criteria
- choose the ready frontier and recommend the smallest useful continuation
- record handoff context that lets another agent work autonomously
- preserve provenance when an existing public issue is promoted into private execution
  ([references/public-provenance.md](references/public-provenance.md))
- absorb discoveries back into the graph when work reveals new reality
- update the active design doc when discoveries change the initiative design rather than only the
  execution graph
- record a code review's findings as a review bead
  ([references/review-beads.md](references/review-beads.md))

## Stop before you start

- The work is a multi-slice initiative, not a single item — it needs a design doc first. The call
  between a direct bead and that path is [references/work-intake.md](references/work-intake.md).
- An epic exists but has no slices — it has not been decomposed yet; run `to-issues`.
- The item is human-gated — stop for sign-off before claiming it (see below).

Deciding *where* implementation happens — branch, worktree, or the main checkout in place — is not
this skill's call. That belongs to the user or the session; this skill hands off whatever item is
next and picks back up once work returns to the graph.

## Who uses it

Any session, from the main checkout or from a worktree. From the main checkout you shape work,
inspect readiness, and maintain the graph. A worktree session may claim, update, split, create, and
close related items as discoveries emerge. That autonomy is intentional: stay anchored to the
assigned item or epic, but do not freeze when work reveals missing scope.

## Human gate

Items flagged for human review need a person's decision before an agent proceeds. The agent
checks for gated items before each new item and treats only flagged items as gated.

Unflagged items are **autonomous**: the agent may pick them up, work them, and close them without
stopping for sign-off. This is the default because most items are small enough that the check-in
adds friction without value. The human-review flag is the intentional exception.

Flag an item for human review when it genuinely needs a decision — scope ambiguity, design
trade-offs, cross-cutting impact, or anything you want to see before work starts. Leave
everything else unflagged so the agent can flow through the ready frontier.

## Operating loop

1. Read `.brain/AGENTS.md` (Project section — project tracker conventions; absent or empty means
   pure defaults), [references/beads.md](references/beads.md) (engine mechanics and native-modeling
   rules), and [references/work-intake.md](references/work-intake.md) (bead vs. design doc), then
   project Brain context and relevant ADRs.
2. Inspect the graph: ready frontier, list, and item detail (commands in
   [references/beads.md](references/beads.md)).
3. Check for human-gated items among the ready set (engine reference covers the command). Recheck
   every iteration: the gated set changes as items close and new ones are created.
4. Select the next ready item:
   - **Human-gated** — stop for sign-off before claiming.
   - **Autonomous** — claim directly and proceed.
5. If the item carries `spec-id design:<slug>`, read `.brain/designs/<slug>.md` before
   implementing. Beads carry execution facts; the design doc carries the design,
   rationale, and file-level scope — do not infer those from the compressed acceptance criteria
   alone.
6. Implement, update notes, and close when acceptance criteria are satisfied. This is manual,
   turn-by-turn work — the human reviews each edit and each `bd close` as it happens — so it
   lands local by default, epic or not. Present what was done and confirm before closing, unless
   the user explicitly asked you to close it. Work originating from an existing public issue may
   land through its public PR collaboration flow
   ([references/public-provenance.md](references/public-provenance.md)). `bd close` remains the
   private close signal.
7. If that close emptied a design-linked epic — no open slices left under an epic carrying
   `spec-id design:<slug>` — run `close-design` before moving on. The design doc is still marked
   `active` and its residue is still unharvested; that is the moment to settle both.
8. When implementation exposes hidden requirements or follow-up work: do the obvious in-scope work
   directly; create or update related items when new work becomes explicit; split or re-slice the
   current item when it is no longer the right shape; adjust dependencies or acceptance when the
   graph is wrong. Put discoveries back into the graph, never into ad hoc todo files.
9. Return to step 2. Continue until the ready frontier is empty or hits a human-gated item
   whose decision you're not present to make.

## Handoff context

When work moves to another agent or session before it closes, record enough that the worker can
act without being spoon-fed: work-item ID, anchor epic (if any), intended scope, required checks,
and review/landing expectations. A branch created for the work uses the canonical name
`<item-id>-<short-slug>` (the issue ID in the configured engine), which supports SessionStart
anchor inference.

## Review beads

Once any code review's findings need to survive the session — the user asks for a review bead, or
it's the natural next step after a review pass, whatever skill or process ran it — see
[references/review-beads.md](references/review-beads.md). It covers the single-pass and multi-pass
shapes a review bead can take, one generalized recipe regardless of which review produced the
findings, and how to recognize an existing bead's shape before operating on it.
