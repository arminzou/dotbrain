# Execution record

The execution record is the recoverable state of one work item under `run-execution`. It
follows the review-bead pattern: native Beads fields own status, assignee, dependencies,
acceptance, and specification links; four flat `dotbrain_` metadata keys hold the item's
queryable current state; headed append-only comments are its evidence history; notes hold
rationale and a resume summary. Writer permissions, claims, actors, and closure follow
[manage-work-graph](../../manage-work-graph/SKILL.md#ownership-and-closure).
Item review, verdicts and exemptions, checkpoint streaks, acceptance/UAT evidence, and finding
dispositions follow [Run Execution](../SKILL.md#item-review-and-acceptance).

## The `dotbrain_` keys

Optional until the item enters `run-execution`. Populate only facts that exist.

| Key | Meaning |
| --- | --- |
| `dotbrain_phase` | `preparing`, `working`, `candidate`, `integrating`, `checking`, `verified`, or `cancelled`. |
| `dotbrain_attempts` | Consecutive failed-check count and approved limit for each checkpoint, keyed by checkpoint reference. |
| `dotbrain_artifacts` | References, each with a `kind`, `purpose`, and `ref`. Purposes are `work` (where the active worker's changes live), `candidate`, `integrated`, and `evidence`. |
| `dotbrain_retro` | `candidate` while the bead holds a `## Retro candidate` comment that `run-retro` has not yet curated; set by the lead, cleared only by `run-retro` after its notebook save. Beads comments do not change an issue's update time, so this flag is what makes a candidate findable. |

```json
{
  "dotbrain_phase": "candidate",
  "dotbrain_attempts": {
    "tests-pass": {"failed": 0, "limit": 3},
    "item-review": {"failed": 1, "limit": 3}
  },
  "dotbrain_artifacts": [
    {"kind": "worktree", "purpose": "work", "ref": "/abs/path/to/worktree"},
    {"kind": "git-branch", "purpose": "candidate", "ref": "short-slug@4f2a9c1"}
  ]
}
```

`verified` means the integrated item passed its agreed acceptance checks. It does not close the
item or bypass a human gate; native status alone decides closure. The phase describes
workflow progress, not a second status system. A blocked item keeps its last phase: the native
`human` label and a `Blocked` comment mark it. The HITL/handoff workflow and sequential/parallel
execution mode belong to the bounded execution, not the item. Beads' own `execution_mode` and documented execution-hint metadata keep their
meanings as advisory routing input.

Review beads belong to review-gate and are never executed here.

## Write method

Use [manage-work-graph's metadata and comment write method](../../manage-work-graph/SKILL.md#metadata-write-method).

## Comment headers

```text
## Dispatched: <worker actor> in <checkout> on <branch> @ <base>
## Dispatched: <worker actor> in <checkout> on <branch> @ <base> (fix round <n>)
## Attempt <n>: PASS | FAIL @ <revision>
## Candidate @ <revision>
## Review <n>: APPROVE | CHANGES @ <revision> (round <r>)
## Review skipped: <reason>
## Review skipped: declined by human — <reason>
## Integrated @ <revision> on <target> (candidate <revision>)
## Accepted @ <revision> on <delivery-branch> (group <group-ref>)
## Blocked @ <revision>
## Held group <group-ref> @ <revision>
## Containment @ <revision>
## Claim moved: <from actor> -> <to actor>
## Cancelled @ <revision>
```

Record `Dispatched` as soon as the runtime identifies the worker, before waiting on it. Its body
holds the worker's runtime, its agent or session ID with how it was launched (`in-session
subagent` or `CLI session`), any launch mechanism no runtime reference documents, and the full
assignment as sent. A fix round's `Dispatched` holds the consolidated assignment and what changed
since the last round, so a fix round or replacement rebuilds its assignment from the item's
records alone. A fix round resumes that worker by ID; a takeover needs to know which worker to
confirm stopped.

A writing worker appends its full report as `Candidate` before returning and returns only its
status line. A lead that writes the change itself, including on a lead-only runtime, records the
same `Candidate` shape.

A launched item or integration reviewer appends its full report as `Review` to every item in its
review boundary, in one command under its own actor, and returns a status line and an index; the
lead routes from the index and reads a body only to dispute it. Before notifying workers or
dispatching repairs, the lead confirms each boundary item has that round's `Review` comment,
copies a missing one from a sibling item, and records the whole report itself only when the
reviewer could not write. A lead-only runtime that launches no reviewer agent needs none of this:
its lead records the independent review it obtained, such as one the human ran in another
session, in the same `Review` shape under its own actor. Recording another agent's review is not authoring it; the
lead still never reviews changes it authored. The report preserves reviewer identity, review number and round,
base/head references, covered items and per-criterion acceptance coverage (including unmet or
unreviewed criteria), per-item verdicts, complete finding wording and severity (`blocker`,
`high`, `medium`, `low`), `file:line`, and material evidence or coverage limits. For an
uncommitted candidate, it includes HEAD and a diff fingerprint so the verdict cannot be mistaken
for approval of HEAD alone.

```bash
bd comments add <item-id> --file <review-file> --actor <lead-actor> --json
```

Confirm a comment the lead copies or records matches the report. Label ownership and
coordination notes as lead additions. A cross-item finding has one responsible worker: name it in
a lead note on every affected item, citing the `Review` comment and finding ID, and route repairs
to the original workers with these references. Preserve disputes as new records and return them
to the reviewer or human; never silently change a verdict. Member records must recover all
findings and review limits without relying on an epic comment or a new batch review bead.

## Integration groups and recovery

Use the existing member beads, comments, and artifact references; no scheduler ledger or group
bead is needed. On every member, record a stable group reference, all included item IDs, group
base/head (or HEAD and diff fingerprint), candidate branch/worktree and integrated revisions,
accepted delivery branch/head, reviewer identity
and report reference, per-member verdict and acceptance coverage, combined check commands/results
with revision and environment, and unresolved coverage gaps. Link shared findings by durable
comment reference and finding ID under the existing ownership rules. A member record must recover
its acceptance boundary without relying on the lead's transcript.

`Integrated` records provisional group integration; `Accepted` records delivery promotion.
Follow [the group procedure](parallel-execution.md#group-candidates-and-promotion).
Record the delivery branch, before/after heads, group reference, refreshed review/check
references, and dependent bases. Charge checkpoint failures to affected members with
finding references; never invent a group counter.

For held groups, record membership, failed/uncovered criteria, evidence and waiting
dependents on every member. `Containment` records accepted bases, isolated candidates,
affected files/resources/consumers, exclusive repair ownership, before/after revisions
and checks. Follow [containment](parallel-execution.md#failed-group-containment) and
[stop scopes](../../iterate-design/SKILL.md#stop-scopes).

A replacement lead identifies work by item, then branch or worktree, then revision; agent IDs do
not survive every restart. It never resumes an `in-session subagent` ID from an ended lead
session: that worker's termination is uncertain under
[claim moves](../../manage-work-graph/SKILL.md#ownership-and-closure). It resumes a
`CLI session` ID only after confirming that session is not running.

Final review reuse follows [review-gate](../../review-gate/SKILL.md#final-branch-review).
Retain the report and provenance references required there on the final review record.

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
   So does a status line whose `Observed` revision differs from the requested review or
   verification head, or from a worker's reported candidate and actual branch head: never
   record such a result as current.
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
   Confirm the stored record matches the result; a worker's report is its `Candidate` comment,
   recorded by the lead from the returned report only when the worker could not. A returned candidate retains its claim and leaves dependents held.

After recording results, choose integration groups, review, fixes, and eligible ready work under
Run Execution's acceptance rules and this reference's linked capacity rules. Keep pending results in the lead's session and
recoverable facts on member beads. Use these records without a separate inbox directory or scheduler ledger.
