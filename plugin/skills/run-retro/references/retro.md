# Private retrospective format

Maintain one plain Markdown `RETRO.md` in the private Brain. Each finding appears once. Use
work-area headings and, per finding, a bold imperative practice, a `When:` trigger, needed limits,
and dated source pointers to the work or review records that hold the evidence. Detailed
chronology stays in those records. Successful practices are marked `Done right` alongside mistakes.
Keep personal preferences in `.brain/AGENTS.md` and human learning in `teach-me`.

## Example

```markdown
# Retrospectives

Timezone: UTC
Review scope: <explicit contribution branches/PRs, or repository integration branch>
Baseline: <repository, branch, initial full commit; earlier history excluded>
Guidance: <links to relevant repository rules, standards, and contributor guidance>
Curation cutoff: 2026-04-06T02:00:00Z
Unreviewed history: <any older range never reviewed, with the reason>
Gaps: <known discovery or source gaps>

## Verification

**Check the integrated commit before declaring work complete.**
When: several workers' changes are combined before closure.

- 2026-04-01 — <work record>: the combined check caught a shared-contract error.
- 2026-04-05 — <review record>: a later integration repeated the same failure.
- Limits: recorded local results only; no shipment or broader productivity claim.
- Enforcement: check — CI runs the combined suite on the integrated head; it would have caught
  the 2026-04-05 failure.
- Pending: Suggest a CI job on the integrated head? a) file work (recommended: the failure
  repeated after a text reminder) b) rule text only c) decline — if unanswered: stays deferred,
  raised again only on new evidence — raised 2026-04-06.

**Done right: preserve user-owned content during reconciliation.**
When: a managed file also holds content the user wrote.

- 2026-03-04 — <work record>.
- Accepted: <public rule link>, merged 2026-03-16 via <PR URL and merge commit>.
```

This example is illustrative, not project evidence. Add optional lines only when useful:
`Enforcement:` for the suggested intervention and its level, or why none fits; `Pending:` for a
decision awaiting the human; `Proposal:` for authorized delivery (upstream/base, push
repository/head, and PR when available); `Hold:` for a blocker or rejected proposal; and
`Accepted:` only after verified adoption. Keep a prepared public wording or patch with its
proposal when needed for interrupted delivery. No YAML findings, schema versions, recurrence
counters, mandatory IDs, duplicate bookkeeping appendix, or sidecar.

## Save

Every writer uses this compare-and-swap save; there is no notebook lock. Exclude `RETRO.md.tmp.*`
in the private repository's local Git exclude file before creating one.

1. Read `RETRO.md` and record its SHA-256 hash before computing changes.
2. Compute every change, including any header update, and write it to an adjacent
   `RETRO.md.tmp.<nonce>` on the same filesystem.
3. Hash `RETRO.md` again. If it is unchanged, atomically replace it with the temporary file and
   read the result back. If it changed, delete the temporary file and do not write.
4. On a conflict, a work session re-reads and retries once; if it conflicts again, its evidence
   stays in the work or review record for the next curation. A curate pass abandons and leaves the
   work to the next run. Neither waits, overwrites, or delays closure of accepted work.

The window between the second hash and the replace is short but not zero. A session write lost
there is still recoverable, because its evidence was recorded in its source record first.

## First-run baseline

If no retrospective exists, establish a baseline from the current checkout and repository
guidance. Start with root instructions and the standards/contributor guides they identify;
read scoped instructions when relevant work reaches that area. Do not recursively load every
document, copy standards into findings, or count reading a rule as evidence. Record missing
or conflicting guidance as a gap, not an invented finding or authority to resolve the conflict.

Record repository identity, current ref and full HEAD, timezone, guidance links, and a curation
cutoff of the initialization time. Earlier records and history are excluded unless explicitly
selected for a focused pass. Save and report initialization; do not capture historical findings,
create public rules, or enable delivery. The repository-scope rules file offer below is the only
public change initialization proposes.

Preserve an existing retrospective and its progress. A new worktree, machine, checkout, or
branch does not trigger reinitialization. If repository identity does not match, retain existing
progress and report the mismatch instead of silently selecting a new baseline.

## Select review scope

Record the human's selected scope in the header, then reuse it across runs:

- **Contributor:** explicitly selected contribution branches or PRs plus their review evidence.
  Do not infer ownership from author names, agent identities, or all commits arriving upstream.
  Upstream changes may supply context; they are not automatically contributor evidence.
- **Repository:** an explicitly selected integration branch plus relevant work/review evidence.
  Repository-wide review is a maintainer choice, not a consequence of installing Dotbrain.

Do not choose between these scopes silently. If none is established, initialization may record
`Review scope: unset`; report the missing choice and do not capture new work until selected.
A scheduled run reports the gap without waiting interactively.

## Rules file offer

Repository scope only, on any pass while the header has no `Rules file:` line or says
`Rules file: offered`, so notebooks initialized earlier are covered too. If the repository has no rules or standards file (a
contributing guide alone does not count), offer once to create root `RULES.md`; if one exists,
record `Rules file: existing <path>` instead; a contributor-scope run never creates a
public file and keeps suggestions private until a suitable upstream file exists. On the user's
explicit yes, seed `RULES.md` only with requirements existing guidance already states, in
[the rule format](rules.md); link it from public `AGENTS.md`; and deliver it through
[run-retro's PR process](pr.md) from a clean target-based checkout. Add `RULES.md` to
`retro.promotion.destinations` without changing `auto-deliver`. Record the outcome in the header:
`Rules file: <PR URL>`, `Rules file: declined` (never offered again), or `Rules file: offered`
when no answer came, such as a scheduled run, which asks again on the next interactive run.
Findings capture normally whatever the answer.

## Curation cutoff and selection

The header's `Curation cutoff:` is a timestamp. Select records changed after it, oldest update
first, within the pass limit:

- work and review items: `bd list --all --updated-after <cutoff> --sort updated --reverse --json` (oldest first), then read
  each selected item's comments for CHANGES verdicts, failed checks, rejected candidates, human
  corrections, defects, and informative successes or recoveries;
- PRs in scope merged or closed since the cutoff, with their reviews;
- incidents the human supplies, regardless of date.

Read linked evidence as needed. Commits and CI support an investigation; they are not walked as a
queue. A comment edit may not update its parent's timestamp, so a date query is a discovery aid,
not proof that every change was found; state that limit. Failed reads leave a gap, not a claim
that the source was empty.

After the save, the cutoff is the update time of the last record whose changes the save contains.
`--updated-after` is strict, so never stop between records that share an update time: finish every
record with the last processed update time, even past the pass limit, or set the cutoff to the
previous update time instead. Never advance it past unread or failed evidence. If changed records updated more than one
scheduling interval ago (one day unless the header records a `Schedule:`) are still past the cutoff
at the start of a pass, an earlier run did not complete: report a stuck cutoff, with this run's
failure reason if it fails too.

An older notebook may carry a Git `Reviewed through:` boundary and an `Unfinished:` frozen range,
and no `Curation cutoff:`. Set the cutoff to the time of the last completed pass the header records,
or to the migration time when none is recorded, and name any uncovered period under `Gaps:`.
Record the frozen range under `Unreviewed history:` with the reason. Never advance it or imply it was
reviewed; it is no longer a queue that must finish before recent records are considered.

## Evidence

Match entries by situation and required practice, not exact wording; amend the existing entry
rather than appending another. Each source pointer links a commit, work/review record, document,
or explicit correction, dated by the original event in the recorded timezone, and says in a few
words what happened. Prefer the original event's date; a later rebase, copy, or retry adds no new
pointer. Distinguish the observed outcome from the inferred practice; retain relevant limits and
contradictory evidence. Several dated pointers show recurrence without a counter.

Findings stay in their work-area section throughout. Preserve proposal links, accepted
destinations, actual adoption dates, holds, and pending decisions when consolidating entries.

## Report format

Write for a human who must act quickly, in plain language with decisions first. Omit empty
sections. Keep the report within about 25 lines and summarize anything beyond that as counts.
Reports are private, so work-record and Brain pointers are allowed for follow-up.

```text
<project> · curate · <run time> · records since <cutoff>

NEEDS YOU (n)
1. <question> — recommended: <option> (<one-line reason>)
   options: a) … b) … c) … · evidence: <pointer> · if unanswered: <consequence>
2. Stuck cutoff: <n> records older than <interval> unprocessed · last error: <reason>

CHANGED (n)
+ <added practice> ← <pointer>
~ <refined practice> — <what changed>
- <retired practice> — <what now covers it>

SKIPPED  <n> already covered · <n> not transferable · <n> unresolved (left in records)
COVERAGE <n> records · limit <hit|not hit> · gaps: <gaps or none>
```

An audit report uses the same rules. It opens with `<project> · audit · scope: <scope>`, then the
keep/revise/stop recommendation in one line, evidence grouped as delivered and used, delivered
but ignored, missed lookup, and repeated failures, per-finding recommendations, cost,
inconclusive questions with their gaps, and the decisions it needs.

## Updates and migration

On a retry, compare existing entries, evidence links, and proposal branches/PRs before adding
anything. Unchanged input causes no rewrite and no report. Reconcile pending PRs even if
curation found nothing new.

Compact repeated prose and promoted entries while retaining useful dated pointers, limits, and
public links. There is no automatic archival or retention limit; do not discard evidence without
an agreed policy.

When updating an older notebook, convert each `Seen n× (dates)` line into dated pointers already
present in its evidence bullets and drop the count. Shorten a long evidence bullet only after
confirming its detail is reachable from the linked record; otherwise keep or relocate the unique
detail. Replace dense pass logs in the header with the curation cutoff, unreviewed history, and
gaps, after their unique evidence and unfinished work are preserved. Render any older YAML as
Markdown, removing mechanical hashes and maps but not meaningful evidence. Do not convert unknown
state into success, rerun historical checks, or add evidence during conversion. If a record cannot
be interpreted safely, leave it intact and report the gap.
