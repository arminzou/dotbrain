# Review beads

How to persist any code review's findings as a bead and operate that bead afterward, whatever
skill, tool, or ad hoc process produced them. A review's own methodology — what it checks, how
rigorously, its finding vocabulary — stays owned by that review. This reference only covers turning
its output into a bead and tracking remediation. `review-gate` selects the review mode; this
file owns its shared record. Item and integration reviews return to the lead, who records them
on member work items using `run-execution`'s
[execution record](../../run-execution/references/execution-record.md), not a separate batch
review bead. The independent reviewer writes no tracker records.

For any returned review, the lead preserves reviewer identity, base/head revision references,
covered items and acceptance coverage, verdicts, full finding wording, severity, stable finding
IDs, and material evidence or coverage limits before dispatching repairs. Ownership and
coordination notes are labeled as lead additions; disputes return to the reviewer or human
without silently changing a verdict. Cross-item findings have one responsible worker, a full
durable finding on that worker's item, and references to its comment and finding ID on all other
affected items. Repair references go to the original workers.

Code review includes change-caused consequences in unchanged consumers and interactions.
Unmet acceptance or a blocker/high regression caused by the reviewed change produces `CHANGES`
wherever its symptom appears; unrelated existing defects and medium/low findings remain
non-blocking discovered work. Missing safety evidence is a reported gap, not a verified claim.

A review bead *is* a review gate, and a gate is human-owned at its close: an agent records the
gate's lifecycle and never closes it on its own judgment. The observed human merge exception
for `code` review beads is in Closing and human review below.

## Verdict vocabulary

| Mode | Result | `verdict` metadata |
| --- | --- | --- |
| `code` | `APPROVE` or `CHANGES` | `approve`, `changes` |
| `readiness` | `READY` or `NOT-READY` | `ready`, `not-ready` |
| `simplify` | Findings only, never blocking | none |

A bare `GO` means only the human's handoff authorization. A single-pass review records its
verdict metadata at creation; a multi-pass code or readiness review starts with `verdict=pending`
and updates it when the verdict is recorded.
Store `target`, `range`, and `modes` for both shapes. Each bead records one mode, so `modes`
is a single-element array; separate modes get separate beads. A `simplify` bead has no `verdict` key;
keep it separate from the `code` bead because their closure rules differ.

## Pick the shape

A review bead runs in one of two shapes. The shape is a property of *when the review finishes
relative to when the bead exists*, not of what produced the findings:

- **Single-pass** — the default. The review already ran to completion; create the bead once, with
  the full record already known. Fits an ordinary diff review, a focused audit, or any review
  finished in one sitting.
- **Multi-pass** — the review itself spans sessions, or its record must survive an interruption
  mid-review — typical of a pre-milestone subsystem gate. Create the bead *before* the review
  starts, and record each pass as it finishes rather than batching at the end.

## Fields common to both shapes

- **Type and priority** — `task` by default, `bug` when the findings are predominantly defects;
  priority follows the worst finding's severity. `--parent` the epic under review, when there is one.
- **Description** — the shape (single-pass or multi-pass), target, selected review mode, and standard: what was reviewed (commit range, PR, files,
  subsystem) and what it was checked against, when that isn't already obvious from the surrounding
  epic or design doc. For a multi-pass review, the standard goes here **before pass 1 and is never
  revised** — it is the review's premise, and a premise edited mid-review is not a premise.
- **Severity** — every finding gets one, whichever review produced it: `blocker` (the next thing
  built on this guarantees rework), `high` (wrong behavior read as truth, lost or duplicated work),
  `medium` (real, contained, fixable later at similar cost), `low` (record in one line, don't spend
  the pass on it). Severity is cost of fixing later ÷ cost now — a shared vocabulary across every
  review skill so findings stay comparable. A finding needs a `file:line` location or it's an
  opinion, not a finding.
- **Acceptance** — every finding restated as a verifiable, outcome-focused criterion, never the
  fix's steps. Self-test: would this still hold if the fix took a different shape?

## Single-pass: notes carry the record

- **Notes** — the compact record, written once and rewritten as remediation changes what's true,
  never a growing log: the mode's result, findings grouped by severity,
  verification evidence actually run, what's next, any open question.
- **Comments** — append-only remediation progress from the moment work starts: a fix applied, a
  follow-up bead filed with its id, evidence gathered, a finding that turned out wrong. Never edit
  or delete a comment; a correction is a new comment, not a rewrite — the record of what was
  actually found and actually fixed is the point, and silently repairing it destroys that. Comments
  track progress *after* the notes are written, not a second place to restate the findings.

## Multi-pass: comments carry the whole record

- **Notes** — stay minimal; the comment stream is the record, not the notes field.
- **Comments** — append one immediately after each pass finishes, never batched at the end, so an
  interrupted review still leaves a usable trail. A pass that found nothing still gets a comment
  saying so — silence and "did not run" must never look alike. Open each with a header line
  carrying what a bare timestamp can't: the pass name and the commit the claim is true of, so a
  later reader knows whether a finding still applies to the tree in front of them.
  ```
  ## Pass <n>: <name> @ <commit>
  ## Correction: <finding-id> @ <commit>
  ## Verdict: APPROVE | CHANGES @ <commit>
  ## Verdict: READY | NOT-READY @ <commit>
  ## Closeout @ <commit>
  ```
  Never edit or delete a comment; a correction to an earlier finding is a new `## Correction:`
  comment, not a rewrite. The newest comment is the current state — there is no status header to
  maintain.
- **`--metadata`** — the current queryable result, separate from the append-only record:
  `'{"verdict":"pending","target":"<commit>","range":"<base>..<head>","modes":["readiness"]}'`. Update `verdict` when the
  call is made. Query `verdict=changes` or `verdict=not-ready` with
  `bd list --metadata-field verdict=<value> --all`; an agent verdict does not discharge the gate.
  A simplify pass records findings without a `## Verdict:` comment or `verdict` metadata.

  ```bash
  bd create "<review title> @ <commit>" \
    --type task --priority 1 --parent <epic-id> \
    --description "Multi-pass readiness review: <the standard — the oracle>" \
    --acceptance "All passes recorded; verdict issued; every finding fixed or filed as its own bead." \
    --metadata '{"verdict":"pending","target":"<commit>","range":"<base>..<head>","modes":["readiness"]}'
  ```
  A review with no epic — a repo-wide audit, a release gate — is a top-level bead; use `--type
  milestone` if it qualifies a release.
- **Verdict and close are separate acts.** The `## Verdict:` comment is not a close. Remediation
  happens after, tracked the same way as single-pass remediation (a fix applied, a follow-up filed,
  evidence, a correction), and a `## Closeout @ <commit>` comment names the disposition of every
  finding before the bead closes.

The review methodology that feeds a multi-pass gate — how the oracle gets fixed, what counts as
evidence, how the suite gets mutation-tested — belongs to whatever skill or process runs that gate,
not to this reference. This only covers the bead shape it produces.

## Recognizing an existing bead

Before operating on a review bead you didn't create yourself this session, check which shape it is:
the description names its shape, and `## Pass` comments identify multi-pass reviews. Verdict
metadata alone does not distinguish the shapes. If the shape cannot be established, ask before
rewriting notes. Apply the matching rules above. The two disciplines are not
interchangeable: rewriting a multi-pass bead's notes as "current state," or editing one of its
comments, destroys the record the shape exists to protect.

## Closing and human review

A review bead is **human-gated by definition**: its lifecycle is a review gate, and only a person
decides when that gate is discharged. Findings fixed, a clean verdict, or acceptance met do not
authorize an agent to close the bead on its own judgment.

An open review bead therefore means its **review gate is incomplete**, in one of these senses:
review in progress, remediation in progress, a clean agent verdict awaiting a human, or a PR
awaiting approval or merge.

- **Agent at closeout** — once every finding is fixed, filed as its own bead, or consciously
  declined, append the `## Closeout @ <commit>` record naming each disposition and surviving
  follow-up ids, add the native `human` label, and leave the bead open with a one-line close
  recommendation. The label is the pending-decision signal; never invent a second status label.
- **Human** — closes it explicitly, or the review bead is discharged by `close-design` as part of a
  design's terminal transition. `bd close` remains the close signal. A `simplify` bead stays open
  until every finding is applied, filed as its own item, or declined; a human close or terminal
  transition must account for those dispositions.
- **Observed human merge** — the lead may close a `code` review bead after observing the human's
  merge of the PR recorded on that bead. Cite that PR and its merge commit in the closeout, then
  close. A PR closed unmerged leaves the bead open. Approval alone is not merge evidence.
  A `readiness` bead has no merge-based exception. A `simplify` bead does not close on merge:
  merging does not decide whether its suggestions are wanted.
- **Findings are not the gate** — remediation a review files (defect fixes, follow-up tasks) are
  ordinary beads: autonomous, agent-claimable, and closable. Only the review bead itself is
  human-terminal. Never leave review-derived work open just because it came from a review.

For an epic gate, make the review bead depend on every scoped implementation bead; it becomes
claimable only after the graph reaches its final review step.
