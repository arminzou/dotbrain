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

A review bead records agent work. The lead applies the evidence and disposition rules in
Closing below; independent review remains required. A genuine unresolved decision or explicit
operator gate still binds, but being a review does not create a human gate.

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
  `bd list --metadata-field verdict=<value> --all`; verdict alone does not establish closure evidence.
  A simplify pass records findings without a `## Verdict:` comment or `verdict` metadata.

  ```bash
  bd create "<review title> @ <commit>" \
    --type task --priority 1 --parent <epic-id> \
    --description "Multi-pass readiness review: <the standard — the oracle>" \
    --acceptance "All passes recorded; required verdict and evidence pass at the exact integrated revision; blocking findings resolved and other findings dispositioned." \
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

## Closing

The lead closes accepted reviews before PR merge, without routine human sign-off. Do not add
the `human` label merely because a bead is a review. An explicit gate for a genuine unresolved
decision and stricter operator instructions still bind; investigate within approved authority
and return scope, authority, or acceptance changes to `grill-decisions`.

- **Code/readiness** — require `APPROVE`/`READY`, respectively, and all required acceptance
  evidence at the exact integrated revision. Blocking findings must be resolved; filing or
  declining a blocker does not resolve it. Other findings require recorded dispositions.
  `CHANGES`, `NOT-READY`, pending verdicts, or failed, missing, or stale evidence hold affected
  work and reviews open. After a changed integrated head, refresh review and checks before closure.
  After a closed `APPROVE`/`READY` review, a later head change (repair, PR feedback, or rebase)
  requires a new review record or reopening before that review counts as current evidence.
- **Simplify** — close once every finding is applied, filed as its own item, or declined with a
  reason within approved scope. Record follow-up IDs and reasons. A clean pass has zero findings
  to disposition. Simplify remains non-blocking for PR readiness; an open simplify bead never
  holds the PR or `FINAL`. A `simplify` bead does not close on merge.
- **Closeout record** — append `## Closeout @ <commit>` with reviewer provenance, exact base/head,
  required verdict and evidence references, every finding ID and disposition, surviving follow-up
  IDs, and coverage gaps. Confirm the current integrated head matches before native `bd close`.
  Preserve the assignee: close under its actor, naming the lead in the reason; never force closure.
- **UAT evidence** — record revision, environment, agreed user journeys, actual checks/results,
  and gaps. An unexercised journey is a gap, never a pass. Missing UAT holds affected work when
  required; it is not an automatic request for the human to check. Investigate and repair within
  remaining limits; preserve containment, retry caps, and finite whole-loop limits on resume.
- **Delivery boundary** — closure grants no PR approval or merge authority, never merges the
  target branch, and never automatically invokes `close-design`. Neither PR approval nor merge
  is a prerequisite for accepted review closure. The design and epic remain active until manually
  invoked terminal closeout. Review-derived follow-up work uses ordinary work closure rules.

For an epic gate, make the review bead depend on every scoped implementation bead; it becomes
claimable only after the graph reaches its final review step.
