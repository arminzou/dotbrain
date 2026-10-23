# Parallel execution and replacement workers

Read this before choosing or dispatching more than one concurrent writing worker, and before a
replacement worker starts.
The default path and review rules remain in [Run Execution](../SKILL.md).

## Choose parallel execution

Choose parallel execution when at least two items in the fixed set are ready and separable, their
mutable outputs and resources can be isolated or exclusively scheduled, and actual worktree
isolation and distinct Beads actors are available. Overlapping files are allowed when behavioral
responsibilities are separable in separate worktrees; an unsettled shared interface is a
prerequisite to settle before dispatch. Otherwise choose sequential execution. State the mode,
behavioral ownership, known file overlap, and resource allocation before dispatch; the human may
override.

When parts of one item could run concurrently, shape them through manage-work-graph before
execution, preserving criteria and finite limits.


## Capacity and isolation

The authorized item count and active writing-worker cap are separate. Unless the human specifies
the cap, select and announce a finite cap from actual runtime capacity, resource isolation, and
stated limits. Account for capacity consumed by the lead and required review and verification
operations, including nested agents. Human gates and explicit budgets and caps remain binding.

Fill available writing slots from eligible ready items inside the fixed scope; refill as workers
finish. A returned candidate frees a writing slot without accepting its item or releasing its
claim. Resume a worker for repair only when a writing slot is available. Reduce concurrency when
integration, checks, or shared resources become bottlenecks; capacity never expands scope or
releases a dependent whose prerequisite is not accepted.

Give simultaneous writers separate worktrees and mutable outputs or resource instances where
possible; schedule genuinely shared resources exclusively. Build outputs, databases, and ports
still constrain parallelism. Actual worktrees, claims, resource ownership, and exclusive
scheduling establish isolation; instructions to avoid collisions do not. Serialize integration
into the target and route needed rebases to the original workers.


## Group candidates and promotion

| Operation | Required input or gate | Result and next operation |
| --- | --- | --- |
| Integrate provisionally | Passing worker checks, coherent group membership, and the accepted delivery head; workers remain assignees. | Create an isolated group candidate branch from the accepted delivery head. For each candidate, rebase the item branch onto the current group candidate, then fast-forward the group candidate with `git merge --ff-only <item-branch>`; never create a merge commit. On conflict, resume the original worker and rerun checks. Keep all members open and dependents held. |
| Integration review and checks | Group base/head, included items, and criteria. | Apply [Run Execution's item review and acceptance](../SKILL.md#item-review-and-acceptance) and check role routing to every member. |
| Promote and apply closure rules | Run Execution's acceptance gate passes for the group. | Fast-forward the delivery branch with `git merge --ff-only <group-branch>`; apply Run Execution's head confirmation and manage-work-graph's native closure. |

- If the delivery head advances before promotion, rebase or rebuild the group candidate from the
  latest accepted delivery head, route conflicts to original workers, and refresh review and
  combined checks before promotion. Serialize promotion and confirm the exact accepted head before
  closing members or releasing dependents. Preserve held group branches and worktrees; independent
  groups start from the accepted delivery head and can be promoted without the held changes.

## Group boundaries

Passing candidates may be provisionally integrated, then reviewed as a coherent group at an exact
integrated revision. Group boundaries follow features, shared interfaces, and independently
verifiable results, not launch waves or whole epics. A group may contain one item. Review promptly
when accepting a completed prerequisite unlocks dependent work; otherwise group related completed
changes. Provisional integration closes no items and releases no dependents.


## Completion handling

Apply [result reconciliation](execution-record.md#completion-handling) before refilling.

## Failed-group containment

Continue unrelated authorized work only with evidence of accepted bases and isolated integration
candidates. A held contribution on a group candidate cannot silently become another item's base.
Before continuing, record the accepted revision, affected files/resources and consumers, ownership,
and containment checks. Preserve failed candidates and worktrees; use accepted bases and isolated
integration candidates while retaining the held contribution and unrelated accepted work.
Reconsidering a failed group as smaller groups requires a new explicit review boundary and fresh
combined acceptance evidence; prior individual verdicts alone are insufficient.
Serialize shared repair with an explicit file/resource boundary and recorded before/after revisions
and checks. Stop affected writers while that resource is exclusively held. If containment cannot
be proven, stop dispatch and integration; apply [iterate-design's stop scopes](../../iterate-design/SKILL.md#stop-scopes)
for shared-state compromise, unresolved decisions, and cancellation.


## Claim moves and replacements

Apply [claim moves](../../manage-work-graph/SKILL.md#ownership-and-closure).

A replacement worker continues in the stopped worker's worktree named by the item's
`work` artifact. Confirm termination before replacement and preserve scope, budgets,
attempt counts, review history, and pending human gates. Follow the runtime reference
for the actual stop, resume, and replacement mechanism.
