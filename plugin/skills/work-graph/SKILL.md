---
name: work-graph
description: Inspect and maintain a project's private Beads work graph, including tasks, dependencies, ownership, acceptance criteria, evidence, and unfinished work. Use for tracker operations or requests to inspect ready work. The chosen engineering workflow owns execution and acceptance procedure.
---

# Work graph

Operate the private execution store exposed through the wired checkout's
`.beads` link. The Brain preserves project understanding, while Beads records
durable execution state. Use the repository's selected engineering workflow to
carry out implementation, arrange review, and decide whether its acceptance
requirements have been satisfied.

## Locate and inspect

Read the applicable repository requirements and project declaration. Run
`bd prime` at the start of a session or after context recovery unless its
protocol is already supplied by the host. Confirm the store with `bd where`.
Use `bd -C <checkout>` when running outside the wired checkout. An unavailable
backend or tracker opt-out is an explicit operation gap. Wiring repairs belong
to `wire-brain`.

Inspect the requested scope using structured, non-interactive output. A ready
query establishes dependency eligibility. Execution authority, work selection,
capacity, and review requirements come from the chosen workflow and applicable
user/repository instructions.

Completion means the target store and requested records are identified and
the operation's prerequisites are known. Do not substitute another project or
an ad hoc tracker when a requested store is unavailable.

## Model work

Read [Native Beads operations](references/beads.md) for field meanings and
dependency direction. Use native types, parentage, status, assignee, dependencies,
and acceptance fields. An initiative's design is linked through `spec_id`.
The design contains intent and architecture, while the graph contains durable
task state. Keep initiative prose in its owning record.

Temporary checklists may describe procedural steps within a task. Record work
that must survive a handoff, dependencies, ownership, and pending improvements
in Beads. Decision trails can explain choices and link their evidence.

Establish outcome-focused acceptance criteria from the adopted scope. A change
to user-owned acceptance or authority requires the corresponding decision.
Recording new evidence does not change what was agreed.

Completion means each requested work item and relationship has the correct
native representation and its durable records remain consistent.

## Apply changes

Pass an explicit actor on every write. Read current state before ownership
changes and use atomic native operations or matching preconditions. The selected
workflow determines which agent holds a task's claim and how delegated work is
accounted for. A claim conflict or failed precondition requires fresh inspection.
Lease expiry alone does not establish that an existing writer has stopped.

Use metadata only for facts the workflow needs that native fields cannot express.
When updating merged metadata, preserve unrelated keys. Store execution evidence
in comments and supporting artifacts, with the revision, environment, checks,
outcomes, and unresolved gaps needed to assess it. Resume notes identify current
state, artifact locations, remaining work, and the next action.

Only close a task when the selected workflow has established its acceptance
evidence and resolved applicable gates. Use native ownership and closure
protections. A task's closure records the specified work outcome. Record PR
or release outcomes separately when relevant. Historical failures and consumed
limits survive status changes and takeover.

For a multi-step operation, inspect actual results after each durable mutation.
If an operation partially succeeds, report what was written and reconcile its
current state before retrying. Preserve data and evidence during recovery.

Completion means the requested changes are confirmed from the store, failed or
pending operations are explicit, and applicable acceptance evidence is linked.

## Report

Return the affected item IDs, actual state changes, evidence locations, and
remaining work or uncertainty. Private work records and identifiers stay in the
private workspace. Derive standalone public guidance through the applicable
context or repository-rule capability when public communication is requested.
