---
name: operate-execution
description: Create, claim, work on, and close issues in the project's private execution graph. Use when filing issues, creating work items, claiming tasks, inspecting the ready frontier, updating work status, or closing completed work — any interaction with the project issue tracker.
---

# Operate Execution

Operate the Brainspace's private execution layer: a typed, prioritized **dependency graph** of
work items. The engine is declared in `project.yaml` (`execution-engine:`). This skill
is engine-agnostic — it owns the model and workflow; the engine's CLI mechanics and native-modeling
rules live in `references/<engine>.md` ([references/beads.md](references/beads.md) for beads).

The dependency graph is the concurrency contract: the **ready frontier** (open items with no open
blockers) is the set safe to claim and run in parallel; blocking edges are the serialization. There
is no separate coordination mechanism.

- **Private execution graph** — work items in the engine's store; this skill owns it and it is the
  source of truth. Never mirror work state into markdown docs, ROADMAPs, task lists, or a public
  issue tracker.
- **Public issue tracker** — handled by `triage-public`; existing public collaboration may be
  promoted inward with a provenance link, but private work is never published outward for tracking.
- **Knowledge layer** — `.brain/CONTEXT.md`, `.brain/adr/`, `.brain/AGENTS.md`; owned by other skills.

## Context files

Read at session start, before inspecting the graph:

1. **`.brain/AGENTS.md`** (Project section) — project tracker conventions shared with
   `triage-public`: linking rules, ADR policy, priority deviations. Absent or empty means pure defaults.
2. **[references/beads.md](references/beads.md)** — engine mechanics and native-modeling rules:
   commands, types, dependencies, status, labels. Swap for the active engine's reference if it changes.
3. **[references/work-intake.md](references/work-intake.md)** — work intake pipeline: when to create a
   issue directly vs when to suggest a design doc + epic. Read to decide how new work enters the graph.

## What this skill owns

- shape epics, tasks, dependencies, and acceptance criteria
- choose the ready frontier and recommend the smallest useful continuation
- recommend an execution mode for ready work (below)
- record handoff context that lets another agent work autonomously
- preserve provenance when an existing public issue is promoted into private execution
- absorb discoveries back into the graph when work reveals new reality
- update the active design doc when discoveries change the initiative design rather than only the
  execution graph

It recommends how to isolate work (below) but does **not** run it: turn-by-turn work happens in the
session, an automation handoff runs through `iterate-design`, and worktree isolation is a runtime
capability, not a mode this skill enters.

## Who uses it

Any session, from the main checkout or from a worktree. From the main checkout you shape work,
inspect readiness, recommend mode, and maintain the graph. A worktree session may claim, update,
split, create, and close related items as discoveries emerge. That autonomy is intentional: stay
anchored to the assigned item or epic, but do not freeze when work reveals missing scope.

## Human gate

Items flagged for human review need a person's decision before an agent proceeds. The agent
checks for gated items before each new item and treats only flagged items as gated.

Unflagged items are **autonomous**: the agent may pick them up, work them, and close them without
stopping for sign-off. This is the default because most items are small enough that the check-in
adds friction without value. The human-review flag is the intentional exception.

Flag an item for human review when it genuinely needs a decision — scope ambiguity, design
trade-offs, cross-cutting impact, or anything you want to see before work starts. Leave
everything else unflagged so the agent can flow through the ready frontier.

## Execution-mode recommendation

When a human-gated ready item is under consideration, recommend where to run it. Isolation is a
per-item choice, not a mode the session enters: pick the cheapest rung that fits, and climb only
when a driver forces it.

- **Main checkout, in place** — the default: one line of work, reviewed as it happens, landing
  local. Most work stays here.
- **Branch in place** (`git switch -c`) — when you want a review surface or the work is safe to
  abandon, but it is still one line of work at a time. A branch isolates history without a second
  working tree.
- **Worktree** — when the work needs a second working tree at once: genuine parallelism (two or
  more trees in flight), an automation handoff you want off the interactive tree, or a long-running
  worker session returned to later. A worktree isolates the working directory on top of history.
  After manual creation, invoke `wire-worktree` if `.brain` or `.beads` is absent, so those links
  reuse the main checkout. Agent workspaces remain project-owned directories.
- **Skip** — the item needs a decision you want to make; leave it for later triage.

Advisory, not a gate; always include a one-line reason. Stop after the recommendation and wait for
the user to respond. Skip means the item stays in the human queue. You recommend the rung; the user
confirms; then the work is cut at that rung — a branch or an `isolation: worktree` dispatch by the
runtime. Autonomous (unflagged) items need no mode recommendation: claim and work them directly.

## Operating loop

1. Read the context files above, then project Brain context and relevant ADRs.
2. Inspect the graph: ready frontier, list, and item detail (commands in `references/beads.md`).
3. Check for human-gated items among the ready set (engine reference covers the command). Recheck
   every iteration: the gated set changes as items close and new ones are created.
4. Select the next ready item:
   - **Human-gated** — recommend mode and stop for sign-off before claiming.
   - **Autonomous** — claim directly and proceed.
5. If the item carries `spec-id design:<slug>`, read `.brain/designs/<slug>.md` before
   implementing. Beads carry execution facts; the design doc carries the design,
   rationale, and file-level scope — do not infer those from the compressed acceptance criteria
   alone.
6. Implement, update notes, and close when acceptance criteria are satisfied. This is manual,
   turn-by-turn work — the human reviews each edit and each `bd close` as it happens — so it
   lands local by default, epic or not. Work originating from an existing public issue may land
   through its public PR collaboration flow. `bd close` remains the private close signal.
7. If that close emptied a design-linked epic — no open slices left under an epic carrying
   `spec-id design:<slug>` — run `close-design` before moving on. The design doc is still marked
   `active` and its residue is still unharvested; that is the moment to settle both.
8. If discoveries change reality, update the graph instead of forcing stale plans to stand.
9. Return to step 2. Continue until the ready frontier is empty or hits a human-gated item
   whose decision you're not present to make.

## Discoveries and re-slicing

When implementation exposes hidden requirements or follow-up work: do the obvious in-scope work
directly; create or update related items when new work becomes explicit; split or re-slice the
current item when it is no longer the right shape; adjust dependencies or acceptance when the graph
is wrong. Put discoveries back into the graph, never into ad hoc todo files.

## Handoff context

When recommending worktree execution or handing work off, record enough that the worker can act
without being spoon-fed: work-item ID, anchor epic (if any), branch/worktree name, intended scope,
required checks, and review/landing expectations. Agent-created branches use the canonical name
`<item-id>-<short-slug>` (the issue ID in the configured engine), which supports SessionStart anchor inference.

## Public provenance and PRs

The link has one direction: promote an existing public issue inward by creating a private item that
references it. The public issue exists for reporter or contributor collaboration; the private item
exists for execution. A private bead, epic, or design never causes a public tracking issue to be
created. A PR may surface any change for review without a companion public issue.

When a PR closes an existing public issue, `Closes #N` closes only that issue; the private item still
needs an explicit close. Mechanics live in [references/beads.md](references/beads.md).

When a private item's work lands through a public PR, the PR body must carry a `Verification`
section restating the verification evidence in audience-safe, plain terms — no `.brain/` paths,
ADR numbers, or `design:` spec-ids. The private item may keep the full evidence in its own notes
or the linked design doc; the PR gets the public rendering only.

Landing here is local review by default because manual, turn-by-turn work is reviewed continuously.
Use a PR when the user wants a review surface or the work is already part of public collaboration;
do not create an issue merely to justify the PR.

## Working habits

- **Check for existing branches first.** Run `git branch -a | grep -i <topic>`; if one exists, ask
  whether to use it or start fresh.
- **Summarize before closing.** Present what was done and confirm, unless the user explicitly asked
  you to close it.
