# Review beads

How to persist any code review's findings as a bead and operate that bead afterward, whatever
skill, tool, or ad hoc process produced them. A review's own methodology — what it checks, how
rigorously, its finding vocabulary — stays owned by that review. This reference only covers turning
its output into a bead and tracking remediation; it applies uniformly to every review, named skill
or not.

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
- **Description** — the target and the standard: what was reviewed (commit range, PR, files,
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
  never a growing log: verdict (approve / request changes), findings grouped by severity,
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
  ## Verdict: GO | NO-GO @ <commit>
  ## Closeout @ <commit>
  ```
  Never edit or delete a comment; a correction to an earlier finding is a new `## Correction:`
  comment, not a rewrite. The newest comment is the current state — there is no status header to
  maintain.
- **`--metadata`** — a multi-pass review's recognizable signal:
  `'{"verdict":"pending","target":"<commit>","range":"<base>..<head>"}'`. Update `verdict` when the
  call is made, so `bd list --metadata-field verdict=no-go --all` finds every outstanding one.

  ```bash
  bd create "<review title> @ <commit>" \
    --type task --priority 1 --parent <epic-id> \
    --description "<the standard this review checks against — the oracle>" \
    --acceptance "All passes recorded; verdict issued; every finding fixed or filed as its own bead." \
    --metadata '{"verdict":"pending","target":"<commit>","range":"<base>..<head>"}'
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
a `metadata.verdict` field or `## Pass`/`## Verdict`/`## Closeout` comment headers mean multi-pass —
apply the multi-pass rules above, not the single-pass ones. The two disciplines are not
interchangeable: rewriting a multi-pass bead's notes as "current state," or editing one of its
comments, destroys the record the shape exists to protect.

## Closing

Close it the same way as any other bead: `bd close --reason` naming the final disposition and any
surviving follow-up ids, once every finding is fixed, filed as its own bead, or consciously
declined.
