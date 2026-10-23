# Parallel execution and replacement workers

Read this before a second writing worker starts, or before a replacement worker starts.
The default path and review rules remain in [Run Execution](../SKILL.md).

## Choose parallel execution

Choose parallel execution when at least two items in the fixed set are ready and separable, their
mutable outputs and resources can be isolated or exclusively scheduled, and actual worktree
isolation and distinct Beads actors are available. Overlapping files are allowed when behavioral
responsibilities are separable in separate worktrees; an unsettled shared interface is a
prerequisite to settle before dispatch. Otherwise choose sequential execution. State the mode,
behavioral ownership, known file overlap, and resource allocation before dispatch; the human may
override.


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
| Integration review | Exact integrated revision, group base, included items, and acceptance criteria. | Required independent review, recorded exemptions, or bounded review-fix rounds; lead records the returned report on members. |
| Check | Exact integrated group revision, combined checks covering every member, and no other verifier running. The lead runs checks unless the caller names a verifier; `iterate-design` reserves its verifier for the in-loop gate. | Revision-bound evidence. Failures or gaps hold the group; changed patches or context affecting acceptance require refreshed review and check coverage. |
| Promote and apply closure rules | Combined checks, required independent review, each member's acceptance evidence, and resolved human gates at the exact integrated revision. | Fast-forward the agreed delivery branch with `git merge --ff-only <group-branch>` and confirm its head equals the reviewed and checked revision. Then write `dotbrain_phase: verified` and apply native item closure through `manage-work-graph`. Provisional integration alone is never acceptance. |

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

A completion notification means a report is available, not that the item passed. Finish the
current integration, promotion, or execution-record update before processing available reports.
Cancellation and safety stops still take effect immediately. Collect available results before
refilling worker slots, starting another integration, or reporting status or completion. Do not
wait for every worker to finish.

For each result:

1. Match the item, runtime agent or session ID, dispatch or fix round, and reported revision to
   the recorded assignment and actual artifacts. Arrival order does not establish which result
   is current. Missing identity or artifacts hold the affected result pending reconciliation.
2. Compare the result with the item's execution record. An already processed duplicate changes
   no phase, claim, attempt count, or acceptance state and triggers no repeated follow-up.
   If recording stopped partway, reconcile the saved evidence before completing the missing writes.
3. Classify a result from an older round, superseded revision, replaced worker, cancelled execution,
   or closed item as stale. Retain new evidence with its source. It cannot overwrite newer state,
   restore a claim, reopen an item, or resume cancelled work. Route relevant findings through the
   existing discovered-work and failure rules instead of silently discarding them.
4. Record a new result and its disposition on the existing item before dispatching follow-up work
   or integrating its candidate. Use the existing execution-record comments and artifact references,
   including the source agent or session ID, dispatch or fix round, revision, evidence, and gaps.
   Confirm the stored record matches the result. A returned candidate retains its claim and leaves dependents held.

After recording results, choose integration groups, review, fixes, and eligible ready work under
the existing acceptance and capacity rules. Keep pending results in the lead's session and
recoverable facts on member beads. Use these records without a separate inbox directory or scheduler ledger.


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
be proven, stop dispatch and integration; shared-state compromise or unresolved scope, safety, or
acceptance decisions stop the entire execution. Cancellation remains a whole-execution stop.


## Claim moves and replacements

Move a claim only for a replacement after the previous worker is confirmed stopped:
`bd update <id> --assignee <new-actor> --force`, recording `Claim moved: <from actor> -> <to actor>`.
Beads refuses to reassign a live claim without `--force`; the confirmed stop is what makes forcing
it legitimate. When termination is uncertain, ask the human.


A replacement worker continues in the stopped worker's worktree named by the item's
`work` artifact. Confirm termination before replacement and preserve scope, budgets,
attempt counts, review history, and pending human gates. Follow the runtime reference
for the actual stop, resume, and replacement mechanism.
