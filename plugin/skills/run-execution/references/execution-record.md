# Execution record

The execution record is the recoverable state of one work item under `run-execution`. It
follows the review-bead pattern: native Beads fields own status, assignee, dependencies,
acceptance, and specification links; three flat `dotbrain_` metadata keys hold the item's
queryable current state; headed append-only comments are its evidence history; notes hold
rationale and a resume summary. Only the lead writes the `dotbrain_` keys and the lead's comment
headers; a writing worker writes only its own claim and its `Attempt` and `Claim moved` comments.
An item reviewer writes its own `Review` comments under its own Beads actor; the lead never
transcribes its verdict or findings. Item review is recorded on the work item, never a review bead.

## The `dotbrain_` keys

Optional until the item enters `run-execution`. Populate only facts that exist.

| Key | Meaning |
| --- | --- |
| `dotbrain_phase` | `preparing`, `working`, `candidate`, `integrating`, `checking`, `verified`, or `cancelled`. |
| `dotbrain_attempts` | Current checkpoint reference, consecutive failed check count, and its approved limit. |
| `dotbrain_artifacts` | References, each with a `kind`, `purpose`, and `ref`. Purposes are `work` (where the active worker's changes live), `candidate`, `integrated`, and `evidence`. |

```json
{
  "dotbrain_phase": "candidate",
  "dotbrain_attempts": {"checkpoint": "tests-pass", "failed": 0, "limit": 3},
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

A passing check ends a failed-checkpoint streak, and another attempt never creates a new bead.
The `item-review` checkpoint counts consecutive `CHANGES` verdicts with limit 3; `APPROVE` resets
the streak. A conflict rebase is not a failed review. Later behavior changes need their own review
before closure even when the earlier candidate was approved.

## Write method

Write only the keys that change, then append history:

```bash
bd update <item-id> --metadata '{"dotbrain_phase":"candidate"}' --json --quiet
bd comments add <item-id> --file <evidence-file> --json
```

Beads merges `--metadata` one level deep: unnamed keys survive, and each named key's value is
replaced whole, so write `dotbrain_attempts` and `dotbrain_artifacts` complete. `--set-metadata`
stores an object as an escaped string; use it, if at all, for `dotbrain_phase` alone.
`bd list --metadata-field dotbrain_phase=<value>` finds open items in a phase; add `--all` to
include closed ones, such as `verified` items. Review beads are `review-gate`'s and are never
executed here.

Check output belongs in evidence comments with revision and environment references. Do not copy
full logs into metadata.

## Comment headers

```text
## Dispatched: <worker actor> in <checkout> on <branch> @ <base>
## Attempt <n>: PASS | FAIL @ <revision>
## Candidate @ <revision>
## Review <n>: APPROVE | CHANGES @ <revision>
## Review skipped: <reason>
## Review skipped: declined by human — <reason>
## Integrated @ <revision> on <target>
## Blocked @ <revision>
## Claim moved: <from actor> -> <to actor>
## Cancelled @ <revision>
```

Each `Review` names the reviewer's actor and findings with severity (`blocker`, `high`, `medium`,
`low`) and `file:line`. The revision identifies the candidate or fix diff reviewed. For an
uncommitted candidate, include HEAD and a diff fingerprint so the verdict cannot be mistaken
for approval of HEAD alone. The reviewer appends its own record:

```bash
bd comments add <item-id> --file <review-file> --actor <reviewer-actor> --json
```

Only unmet acceptance or a `blocker` or `high` finding in the item's diff produces `CHANGES`.
Other findings accompany `APPROVE` and the lead files them as discovered work. `Review skipped`
is the lead's record of an exemption or the human's explicit decline, not a reviewer verdict.
