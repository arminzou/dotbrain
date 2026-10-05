---
name: manage-work-graph
description: Maintains the project's private work graph — files, shapes, links, claims, records outcomes for, and closes work items. Use for any interaction with the project issue tracker — filing work items, inspecting the ready frontier, claiming, updating status, applying closure. Hands implementation of an item or finite batch to execute-workflow. NOT for decomposing a design doc into an epic (to-issues), formalizing an initiative (to-design), closing one out (close-design), or triaging public issues (triage-public).
---

# Manage Work Graph

Maintain the Brainspace's private **work graph**: a typed, prioritized dependency graph of work
items that says what work exists and what it depends on. The engine is declared in `project.yaml`
(`execution-engine:`) and is beads in practice: this skill and the design-lifecycle skills use
`bd` directly. This file owns the model and graph maintenance;
[references/beads.md](references/beads.md) owns how to express work in beads' native fields.

Three terms stay distinct:

- **Work graph** — the work items and their dependency edges. The **ready frontier** (open items
  with no open blockers) is the set eligible to start; blocking edges are the serialization.
- **Execution graph** — how an agent team carries out a fixed set of items: dispatch, integration,
  checks, and closure order. `execute-workflow` owns it; it lives in the lead's session, not in
  the tracker.
- **Execution record** — the recoverable facts on an item under execution: native status and
  assignee, a `dotbrain` metadata object, and headed evidence comments. `execute-workflow` owns
  its contents ([its reference](../execute-workflow/references/execution-record.md)).

Boundaries:

- **Private work graph** — work items in the engine's store; this skill owns it and it is the
  source of truth. Never mirror work state into markdown docs, ROADMAPs, TodoWrite/task lists, or
  a public issue tracker.
- **Public issue tracker** — handled by `triage-public`; existing public collaboration may be
  promoted inward with a provenance link, but private work is never published outward for tracking.
  See [references/public-provenance.md](references/public-provenance.md) when work crosses that
  boundary.
- **Knowledge layer** — `.brain/CONTEXT.md`, `.brain/adr/`, `.brain/AGENTS.md`; owned by other skills.

## What this skill owns

- work intake: a direct work item or the design-doc path ([references/work-intake.md](references/work-intake.md))
- shape epics, tasks, dependencies, and acceptance criteria
- read the ready frontier within an authorized scope and recommend the smallest useful continuation
- ownership: claims and assignees on work items
- record item outcomes and absorb discoveries back into the graph when work reveals new reality
- apply closure rules: native closure when acceptance evidence passes and item-level human gates
  are resolved
- preserve provenance when an existing public issue is promoted into private work
  ([references/public-provenance.md](references/public-provenance.md))
- record a code review's findings as a review bead
  ([references/review-beads.md](references/review-beads.md))
- park a concept for later learning on a learning bead
  ([references/learning-beads.md](references/learning-beads.md))

Implementing an item — dispatch, integration, checks, bounded repair, escalation, and recovery — is
`execute-workflow`'s. A plain request to do the work starts it.

## Stop before you start

- The work is a multi-item initiative, not a single item — it needs a design doc first. The call
  between a direct work item and that path is [references/work-intake.md](references/work-intake.md).
- An epic exists but has no child work items — it has not been decomposed yet; run `to-issues`.
- The item is human-gated — stop for sign-off before claiming it (see below).
- The item is a `learn:` bead (label `learning`) — it tracks the operator's learning, not work;
  `teach-me` resumes and updates it.

Deciding *where* implementation happens — branch, worktree, or the main checkout in place — is not
this skill's call. That belongs to the user, the session, or `execute-workflow`'s lead.

## Who writes the graph

Roles follow the agent team: the **lead** runs one execution and dispatches **workers**; the
**assignee** is the actor holding an item's claim.

- Without delegated workers, the session doing the work is the lead and may shape, claim, update,
  split, create, and close items as discoveries emerge.
- During an execution with delegated workers, the lead is the only agent that changes the work
  graph and edits the active design doc. A delegated worker writes only its own claim and, when
  assigned, evidence comments on its own item. It returns discovered work and design-relevant
  learning to the lead, who records them.

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

1. On a new session or after context recovery, run `bd prime` for the Beads protocol. dotbrain
   injects no Beads context; skip it only when the operator's own Beads hook already supplied it. Then read `.brain/AGENTS.md` (Project section — project tracker conventions; absent or empty means
   pure defaults), [references/beads.md](references/beads.md) (engine mechanics and native-modeling
   rules), and [references/work-intake.md](references/work-intake.md) (bead vs. design doc), then
   project Brain context and relevant ADRs.
2. Inspect the graph with structured, non-interactive output: ready frontier, list, and item detail
   (commands in [references/beads.md](references/beads.md)).
3. Check for human-gated items among the ready set (engine reference covers the command). Recheck
   every iteration: the gated set changes as items close and new ones are created.
4. Select the next ready item, skipping learning beads (label `learning`), which are not work:
   - **Human-gated** — stop for sign-off before claiming.
   - **Autonomous** — claim directly and proceed.
5. If the item carries `spec-id design:<slug>`, read `.brain/designs/<slug>.md` before
   implementing. Beads carry execution facts; the design doc carries the design,
   rationale, and file-level scope — do not infer those from the compressed acceptance criteria
   alone.
6. Hand implementation to `execute-workflow` with the selected item or finite batch. When it
   returns passing acceptance evidence, apply closure here. Present what was done and confirm
   before closing, unless the user explicitly asked you to close it. Review beads are the exception: never close one —
   record its closeout and leave it for the human (see Review beads below). Work originating from
   an existing public issue may land through its public PR collaboration flow
   ([references/public-provenance.md](references/public-provenance.md)). `bd close` remains the
   private close signal.
7. If that close emptied a design-linked epic — no open work items left under an epic carrying
   `spec-id design:<slug>`, ignoring its open review beads — run `close-design` before moving on.
   Review beads never close autonomously, so an epic whose only open children are review beads has
   reached its final review step, not a stall. The design doc is still marked `active` and its
   residue is still unharvested; that is the moment to settle both, and `close-design` discharges
   the review beads with it.
8. When implementation exposes hidden requirements or follow-up work: do the obvious in-scope work
   directly; create or update related items when new work becomes explicit; split or reshape the
   current item when it is no longer the right shape; adjust dependencies or acceptance when the
   graph is wrong. Put discoveries back into the graph, never into ad hoc todo files.
9. Return to step 2. Continue until the ready frontier is empty or hits a human-gated item
   whose decision you're not present to make.

## Handoff context

When work moves to another agent or session before it closes, record enough that the next
assignee can act without being spoon-fed: work-item ID, anchor epic (if any), intended scope, required checks,
review/landing expectations, and the bead's current state: done, next, and any open question. A branch created for the work uses the canonical name
`<item-id>-<short-slug>` (the issue ID in the configured engine), which supports SessionStart
anchor inference.

## Review beads

Once any code review's findings need to survive the session — the user asks for a review bead, or
it's the natural next step after a review pass, whatever skill or process ran it — see
[references/review-beads.md](references/review-beads.md). It covers the single-pass and multi-pass
shapes a review bead can take, one generalized recipe regardless of which review produced the
findings, and how to recognize an existing bead's shape before operating on it.

## Learning beads

When the operator asks to park a concept for later learning, see
[references/learning-beads.md](references/learning-beads.md). It covers the path and backlog bead
shapes, the concept comment, and how to file one without leaving the work underway.
