# Ownership and recovery

Beads holds durable work state. The coordinator owns task claims; native workers
own bounded assignments and candidate artifacts, not independent copies of task
status. Give each coordinator run a distinct actor and record its native run
identity. A replacement does not impersonate the old actor. Use an explicit actor
for every tracker write and `work-graph` for field and dependency semantics.

## Claims and candidate evidence

Inspect the task and ready frontier before `bd update TASK --claim --actor COORDINATOR`.
Check the actual result; a conflict never grants ownership. Record native worker
IDs separately from the coordinator actor. A useful task comment contains:

- Coordinator actor, task ID, accepted scope, criteria, and current limits.
- Each actual native worker ID, assignment/owned resources, worktree and branch.
- Returned candidate revision and the native result that returned it, actual
  checks, independent verification, and unresolved gaps.
- Integrated revision, remaining work, artifact locations, and next action.

Use existing comments/metadata without replacing unrelated fields. Write long
evidence with a file tool, then use `bd comments add TASK --file FILE --actor COORDINATOR`.
Git revisions and native completion results corroborate a report; do not invent
worker IDs or treat a branch name alone as a candidate. Preserve failed checks
and prior limits after repair, replacement, or task status changes.

## Interruption and pickup

Before a planned stop, collect current worker states and preserve candidate
branches, uncommitted files, and verification evidence. Record unfinished work
and the resume point in Beads; update relevant private understanding through
`maintain-brain`. Keep tasks open when evidence is incomplete. Do not reset a
budget, release a claim, or delete a worktree merely to make the handoff tidy.

A fresh coordinator reads the task, comments, dependencies, relevant Brain
records, and actual Git state. Reconcile done versus pending and distinguish
verified constraints from hypotheses. Inspect every affected writer's authority.
Silence, lease expiry, a summary, or a parent process disappearing does not prove
that all delegated writers stopped. Use native lifecycle results and independent
process/worktree evidence appropriate to the runtime.

If the old coordinator or any affected writer has uncertain write authority,
record the hold and required operator resolution without taking its claim or
starting a competing writer. Preserve existing artifacts. An operator decision
does not itself prove process termination: establish the affected writers are
stopped or have explicitly relinquished writes before proceeding.

Once authority is established, reinspect the observed owner and transfer with a
guard. The qualified Beads command form is:

```text
bd update TASK --if-assignee OLD --assignee NEW --actor NEW --json
```

Do not combine `--if-assignee` with `--claim` or `--force`. A failed guard requires
fresh inspection, not an unguarded retry. Confirm returned and persisted owner
and status before continuing. Preserve criteria, dependency edges, comments,
attempts, and consumed limits. A closed/changed task is reconciled as current
state; takeover does not reopen accepted work automatically.

## Replacement and late results

A coordinator can replace a worker after confirming the original writer stopped
or relinquished the assigned resources. Keep its artifacts and attempts, record
the replacement's actual identity and ownership, and delegate under the same
coordinator claim. Uncertain writers retain the hold above.

Before applying any late result, compare its task, assignment, coordinator
ownership, branch, and candidate against the current record. A result from an
obsolete assignment is preserved as evidence and reported, not merged or used
to close current work. A new candidate needs verification at that candidate and
integration context. Completion of an old worker never silently overwrites a
replacement's result or clears another coordinator's claim.

## Closure

Verify the actual integrated candidate and record acceptance before ordinary
`bd close TASK --actor COORDINATOR --json`. Do not force closure past dependency,
ownership, or operator gates. Accepted prerequisites close before dependent work
is selected. Failed/inconclusive checks and uncertain owners stay explicit.
Record any PR/release outcome independently of this task transition.
