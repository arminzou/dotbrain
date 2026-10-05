# Execution record

The execution record is the recoverable state of one work item under `execute-workflow`. It
follows the review-bead pattern: native Beads fields own status, assignee, dependencies,
acceptance, and specification links; a small `dotbrain` metadata object holds the item's
queryable current state; headed append-only comments are its evidence history; notes hold
rationale and a resume summary. Only the lead writes it.

## The `dotbrain` object

Optional until the item enters `execute-workflow`. Populate only facts that exist.

| Field | Meaning |
| --- | --- |
| `phase` | `preparing`, `working`, `candidate`, `integrating`, `checking`, `verified`, `awaiting_human`, or `cancelled`. |
| `attempts` | Current checkpoint reference, consecutive failed check count, and its approved limit. |
| `artifacts` | References, each with a `kind`, `purpose`, and `ref`. Purposes are `work` (where the active worker's changes live), `candidate`, `integrated`, and `evidence`. |

```json
{"dotbrain": {
  "phase": "candidate",
  "attempts": {"checkpoint": "tests-pass", "failed": 0, "limit": 3},
  "artifacts": [
    {"kind": "worktree", "purpose": "work", "ref": "/abs/path/to/worktree"},
    {"kind": "git-branch", "purpose": "candidate", "ref": "item-123-short-slug@4f2a9c1"}
  ]
}}
```

`verified` means the integrated item passed its agreed acceptance checks. It does not close the
item or bypass a human gate; native status is the authority for closure. The phase describes
workflow progress, not a second status system. Interactive or handoff mode belongs to the
execution, not the item. Beads' own `execution_mode` and documented execution-hint metadata keep
their meanings as advisory routing input.

Successful verification ends a failed-checkpoint streak. Worker replacement and resume do not reset
an unresolved streak. A human-authorized extension records the decision and new limit and keeps the
history. Another attempt never creates a new bead.

## Write method

Beads merges `--metadata` one level deep: other top-level keys survive, and the whole `dotbrain`
value is replaced, so a partial object drops omitted fields.

1. Read: `bd show <item-id> --json --quiet`.
2. Reconcile claim, checkpoint, and artifact facts, preserving unknown fields inside `dotbrain`.
3. Write the complete object: `bd update <item-id> --metadata '{"dotbrain":{...}}' --json --quiet`.
4. Read again and check the stored object and the other top-level keys.
5. Append history: `bd comments add <item-id> --file <evidence-file> --json`.

Never use `--set-metadata` for the namespace: it stores a JSON object as an escaped string and
treats a dotted key as a literal name. `bd list --has-metadata-key dotbrain` finds items carrying
the object. `--metadata-field` matches top-level keys only, so filter `phase` from JSON output.
Review beads are `review-gate`'s and are never executed here.

Check output belongs in evidence comments with revision and environment references. Do not copy
full logs into metadata.

## Comment headers

```text
## Dispatched: <worker actor> in <checkout> on <branch> @ <base>
## Attempt <n>: PASS | FAIL @ <revision>
## Candidate @ <revision>
## Integrated @ <revision> on <target>
## Blocked @ <revision>
## Claim moved: <from actor> -> <to actor>
## Cancelled @ <revision>
```

A worker may add `Attempt` and `Claim moved` comments on its own item; every other header is the
lead's.
