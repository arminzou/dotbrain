# Execution record

The execution record is the recoverable state of one work item under `run-execution`. It
follows the review-bead pattern: native Beads fields own status, assignee, dependencies,
acceptance, and specification links; three flat `dotbrain_` metadata keys hold the item's
queryable current state; headed append-only comments are its evidence history; notes hold
rationale and a resume summary. Only the lead writes the `dotbrain_` keys and the lead's comment
headers, including `Claim moved`; a writing worker writes only its own claim and its `Attempt`
comments.
The independent reviewer returns its report without tracker writes. The lead owns `Review`
comments on affected member work items, preserving reviewer provenance and the complete
findings as specified below. Item and integration reviews never create a batch review bead.
The worker remains assignee until closure. The lead writes metadata under its own actor and closes
under the worker's actor, naming itself in the close reason, because Beads lets only the assignee
close; a fix round changes phase and history, not the claim. `Claim moved` records only replacement
of a worker confirmed stopped.

## The `dotbrain_` keys

Optional until the item enters `run-execution`. Populate only facts that exist.

| Key | Meaning |
| --- | --- |
| `dotbrain_phase` | `preparing`, `working`, `candidate`, `integrating`, `checking`, `verified`, or `cancelled`. |
| `dotbrain_attempts` | Consecutive failed-check count and approved limit for each checkpoint, keyed by checkpoint reference. |
| `dotbrain_artifacts` | References, each with a `kind`, `purpose`, and `ref`. Purposes are `work` (where the active worker's changes live), `candidate`, `integrated`, and `evidence`. |

```json
{
  "dotbrain_phase": "candidate",
  "dotbrain_attempts": {
    "tests-pass": {"failed": 0, "limit": 3},
    "item-review": {"failed": 1, "limit": 3}
  },
  "dotbrain_artifacts": [
    {"kind": "worktree", "purpose": "work", "ref": "/abs/path/to/worktree"},
    {"kind": "git-branch", "purpose": "candidate", "ref": "item-123-short-slug@4f2a9c1"}
  ]
}
```

`verified` means the integrated item passed its agreed acceptance checks. It does not close the
item or bypass a human gate; native status is the authority for closure. The phase describes
workflow progress, not a second status system. A blocked item keeps its last phase: the native
`human` label and a `Blocked` comment mark it. The HITL/handoff workflow and sequential/parallel
execution mode belong to the bounded execution, not the item. Beads' own `execution_mode` and documented execution-hint metadata keep their
meanings as advisory routing input.

A passing check ends only its own checkpoint's streak, and another attempt never creates a new
bead. The `item-review` checkpoint counts consecutive `CHANGES` verdicts with limit 3; only
`APPROVE` resets it, so a worker's passing checks during a fix round leave it intact. A conflict rebase is not a failed review. Later behavior changes need their own review
before closure even when the earlier candidate was approved.

## Write method

Write only the keys that change, then append history:

```bash
bd update <item-id> --metadata '{"dotbrain_phase":"candidate"}' --json --quiet
bd comments add <item-id> --file <evidence-file> --json
```

Beads merges `--metadata` one level deep: unnamed keys survive, and each named key's value is
replaced whole, so write `dotbrain_attempts` and `dotbrain_artifacts` complete: every checkpoint's
entry, not only the one that changed. `--set-metadata`
stores an object as an escaped string; use it, if at all, for `dotbrain_phase` alone.
`bd list --metadata-field dotbrain_phase=<value>` finds open items in a phase; add `--all` to
include closed ones, such as `verified` items. Review beads are `review-gate`'s and are never
executed here.

Check output belongs in evidence comments with revision and environment references. Do not copy
full logs into metadata.

Write each comment file so its text arrives verbatim on Windows, macOS, and Linux, in a temporary
location outside the project. Prefer the runtime's own file-writing tool. From a shell, use a
quoted heredoc in bash or zsh, including Git Bash on Windows (`cat > <file> <<'EOF'`), or a
single-quoted here-string in PowerShell 7 (`@'...'@ | Set-Content -Encoding utf8NoBOM <file>`); the
quoting keeps `$` and backslashes literal. Never build comment text with `printf` or `echo -e`:
they turn the backslashes in a Windows path into control characters.

## Comment headers

```text
## Dispatched: <worker actor> in <checkout> on <branch> @ <base>
## Dispatched: <worker actor> in <checkout> on <branch> @ <base> (fix round <n>)
## Attempt <n>: PASS | FAIL @ <revision>
## Candidate @ <revision>
## Review <n>: APPROVE | CHANGES @ <revision>
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

Record `Dispatched` as soon as the runtime identifies the worker, before waiting on it, and put the
runtime's agent or session ID in its body: a fix round resumes that worker by ID, and a takeover
needs to know which worker to confirm stopped.

Before notifying workers or dispatching repairs, the lead appends the returned structured
review to affected member items under its own actor. The reviewer writes no tracker records.
Preserve reviewer identity, review number, base/head references, covered items and acceptance
coverage, per-item verdicts, complete finding wording and severity (`blocker`, `high`, `medium`,
`low`), `file:line`, and material evidence or coverage limits. For an uncommitted candidate,
include HEAD and a diff fingerprint so the verdict cannot be mistaken for approval of HEAD alone.

```bash
bd comments add <item-id> --file <review-file> --actor <lead-actor> --json
```

Confirm the stored comment text matches the returned review before repair dispatch. Label
ownership and coordination notes as lead additions. A cross-item finding has one responsible
worker: record the full finding on that worker's item, with its stable finding ID, and link its
durable comment and finding ID from every other affected item. Route repairs to the original
workers with these references. Preserve disputes as new records and return them to the reviewer
or human; never silently change a verdict. Member records must recover all findings and review
limits without relying on an epic comment or a new batch review bead.

Unmet acceptance or a `blocker` or `high` regression caused by the reviewed changes produces
`CHANGES` wherever its symptom appears, including unchanged consumers and interactions.
Medium/low findings and unrelated existing defects accompany `APPROVE` and the lead files
them as discovered work. Missing evidence remains a gap, not a verified safety claim. `Review skipped`
is the lead's record of an exemption or the human's explicit decline, not a reviewer verdict.

## Integration groups and recovery

Use the existing member beads, comments, and artifact references; no scheduler ledger or group
bead is needed. On every member, record a stable group reference, all included item IDs, group
base/head (or HEAD and diff fingerprint), candidate branch/worktree and integrated revisions,
accepted delivery branch/head, reviewer identity
and report reference, per-member verdict and acceptance coverage, combined check commands/results
with revision and environment, and unresolved coverage gaps. Link shared findings by durable
comment reference and finding ID under the existing ownership rules. A member record must recover
its acceptance boundary without relying on the lead's transcript.

`Integrated` names the isolated group candidate and means provisional until required review,
combined checks, member acceptance, and human gates pass at that exact revision. Keep the delivery
branch at its last accepted revision. After fast-forward promotion, record `Accepted` on each member
with the delivery branch, its before/after heads, group reference, and review/check evidence; confirm
the delivery head equals the reviewed and checked revision before closure. Record dependent bases
containing those accepted prerequisites. If the delivery head advances before promotion, rebase or
rebuild the candidate from the latest accepted head and refresh review and combined checks.
When patches or integration context affect coverage, mark prior evidence
stale and record refreshed review/check evidence; never treat an old verdict as approval of a new
head. Preserve each member's own checkpoint counts: charge failures to affected members with their
checkpoint and finding references, not automatically to every group member or a new group counter.

For a failed or incomplete group, append `Held group` on every member with membership, failed or
uncovered criteria, evidence references, and waiting dependents. Keep claims, original worker IDs,
worktrees, candidate artifacts, limits, attempts, and review history. Before unrelated work proceeds,
append `Containment` with accepted bases, isolated candidates, affected files/resources/consumers,
exclusive repair ownership where needed, and before/after revisions and containment checks.
Preserve held group candidate branches/worktrees separately from the accepted delivery head.
Independent groups can be promoted without the held changes; never reset or rewrite the delivery
branch to recover. Preserve unrelated accepted work; missing containment evidence holds dispatch
and integration.
Shared-state compromise, unresolved scope/safety/acceptance decisions, and cancellation stop the
execution. The human decides exhausted retries; a replacement never resets attempt history.

For final review reuse, retain the explicit whole-branch base-to-exact-final-head report, all scoped
items, interactions and design-conformance coverage, independent reviewer provenance, and check
references. Link it from the final review record; a last-group-only report is insufficient.
