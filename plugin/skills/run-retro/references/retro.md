# Private retrospective format

Maintain one plain Markdown `RETRO.md` in the private Brain. Each finding appears once.
Use work-area headings, a bold imperative practice, a short reason, dated evidence bullets,
and `Seen n× (dates)`. Successful evidence is marked `Done right` alongside mistakes.
Keep personal preferences in `.brain/AGENTS.md` and human learning in `teach-me`.

## Example

```markdown
# Retrospectives

Timezone: UTC
Review scope: <explicit contribution branches/PRs, or repository integration branch>
Baseline: <repository, branch, initial full commit; earlier history excluded>
Guidance: <links to relevant repository rules, standards, and contributor guidance>
Reviewed through: <repository, branch, full commit>
Other evidence reviewed: <selected work/review records and cutoff>
Unfinished: none

## Verification

**Check the integrated commit before declaring work complete.**
Individual worker checks do not establish that their combined changes work.

- 2026-04-01 — <evidence>: the combined check caught a shared-contract error.
- 2026-04-03 — Done right: <evidence> tied review and checks to the same head.
- 2026-04-05 — <independent evidence>: a later integration repeated the same failure pattern.
- Limits: recorded local results only; no shipment or broader productivity claim.
- Seen 3× (2026-04-01, 2026-04-03, 2026-04-05).
- Proposal: <public PR URL>, pending.

**Preserve user-owned content during reconciliation.**

- Evidence: <references to independently dated events>.
- Seen 3× (2026-03-04, 2026-03-09, 2026-03-15).
- Accepted: <public rule link>, merged 2026-03-16 via <PR URL and merge commit>.
```

This example is illustrative, not project evidence. Add optional lines only when useful:
`Suggestion:` for an eligible practice and proposed file awaiting the user's decision,
`Proposal:` for authorized delivery (upstream/base, push repository/head, and PR when available),
`Hold:` for a blocker or rejected proposal, and `Accepted:` only after verified adoption.
Keep a prepared public wording or patch with its proposal when needed for interrupted delivery.
No YAML findings, schema versions, mandatory IDs, duplicate bookkeeping appendix, or sidecar.

## First-run baseline

If no retrospective exists, establish a baseline from the current checkout and repository
guidance. Start with root instructions and the standards/contributor guides they identify;
read scoped instructions when relevant work reaches that area. Do not recursively load every
document, copy standards into findings, or count reading a rule as an occurrence. Record missing
or conflicting guidance as a gap, not an invented lesson or authority to resolve the conflict.

Record repository identity, current ref and full HEAD, timezone, guidance links, initialization
time, and `Unfinished: none`. Mark this commit as the starting boundary, not proof its history
was reviewed. Exclude earlier commits, pre-existing contribution work, and uncommitted changes
unless explicitly selected for a historical pass. An empty repository has no commit baseline;
its first later commits are eligible within the selected scope. Save and report initialization;
do not automatically capture historical findings, create public rules, or enable delivery.
The repository-scope rules file offer below is the only public change initialization proposes.

Preserve an existing retrospective and its progress. A new worktree, machine, checkout, or
branch does not trigger reinitialization. If repository identity or ancestry does not match,
retain existing progress and report the mismatch instead of silently selecting a new baseline.

## Select review scope

Record the human's selected scope in the header, then reuse it across runs:

- **Contributor:** explicitly selected contribution branches or PRs plus their review evidence.
  Do not infer ownership from author names, agent identities, or all commits arriving upstream.
  Upstream changes may supply context; they are not automatically contributor evidence.
- **Repository:** an explicitly selected integration branch plus relevant work/review evidence.
  Repository-wide review is a maintainer choice, not a consequence of installing Dotbrain.

Do not choose between these scopes silently. If none is established, initialization may record
`Review scope: unset`; report the missing choice and do not capture new work until selected.
A nightly job reports the gap without waiting interactively. New source branches/PRs require
an explicit starting boundary or requested range; do not apply another branch's boundary to them.
For several selected sources, record each boundary as ordinary header bullets, not a new ledger.

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
when no answer came, such as a nightly run, which asks again on the next interactive run.
Findings capture normally whatever the answer.

## Review progress

Keep only a short header describing what was actually reviewed and what remains. Record the
counting timezone (default UTC), Git repository/ref and full reviewed commit, other evidence
scope and cutoff, excluded history, gaps, and unfinished work. Use ordinary lines or bullets.
For an interrupted pass, name the fixed range and remaining records in `Unfinished`; resume
those before extending coverage. Persist findings before advancing the reviewed boundary.

After initialization, review new work forward from the selected source's saved boundary
(the baseline until a substantive pass completes), oldest unreviewed first. Freeze the selected
head and evidence cutoff before review. Use `previous..selected-head` only after verifying
ancestry and applying the recorded review scope. If history was rewritten or the old
commit is unavailable, retain the old boundary and report the gap; any recovery range must
be explicit. An empty repository has an empty Git range.

Historical review requires an explicit range and is reported separately; it does not move the
normal forward boundary or silently turn pre-baseline history into a backlog. Read current
guidance relevant to the reviewed work on later runs, rather than treating baseline rules as
frozen policy. Update guidance links if their locations change; a baseline is not a snapshot
database. A proposed practice cannot override newer accepted rules.

Inspect relevant work/review records, including closed items, and supplied corrections within
the declared scope. Include records linked from reviewed changes and explicitly requested
older records. A comment edit may not update its parent's timestamp: a date query is a
discovery aid, not proof that all changes were found. Do not crawl every historical comment
or maintain per-record hashes to promise exhaustive change detection. Report the selected
scope honestly; an older unlinked edit can be missed. Failed reads leave a gap, not a claim
that the source was empty or completely reviewed.

## Evidence and recurrence

Match entries by the situation and required practice, not exact wording. Amend the existing
entry rather than appending another. Each evidence bullet links a commit, work/review record,
document, or explicit correction and says what happened. Distinguish the observed outcome
from the inferred practice; retain relevant limits and contradictory evidence.

Count distinct evidence dates in the recorded timezone, never review-run dates. Several
events on one day count once. Copied reports, retries, wording edits, and rebased versions of
the same event add no occurrence or date. Prefer the original event's date; for a commit use
its author timestamp unless stronger evidence locates the actual event. Later commit or review
timestamps alone do not move that date. Link corroborating sources in the existing bullet.
Undated or uncertain evidence stays useful but uncounted. Correct the date list and Seen count
if evidence is corrected or withdrawn; never invent a date to reach the threshold.

Three supported dates make a finding eligible for a public proposal, not an adopted rule.
Follow [promotion](promotion.md) for delivery authority and acceptance. Without authority,
keep a private suggestion. Findings stay in their work-area section throughout. Add an
`Accepted:` line only after verified adoption; no separate `Promoted` section is needed.
Preserve PR links, accepted destinations, actual
adoption dates, and unresolved dispositions when consolidating entries.

## Updates and maintenance

Use the single-writer and atomic-save process in the skill. On a retry, compare existing
entries, evidence links, and proposal branches/PRs before adding anything. Unchanged evidence
does not change recurrence. Advance only the boundary actually reviewed and saved; retain
remaining work and source gaps. Reconcile pending PRs even if capture found nothing new.

Compact repeated prose and promoted entries while retaining useful dated evidence, limits,
and public links. Promotion does not make the file bounded; there is no automatic archival
or retention limit. Do not create an archive or discard evidence without an agreed policy.

When updating an older structured notebook, render the existing facts, evidence references,
supported dates, progress bounds, unfinished work, and proposal/acceptance details as Markdown.
Remove duplicated YAML and mechanical hashes/maps, not meaningful evidence or known gaps.
Do not convert unknown state into success, rerun historical checks, or add recurrence during
conversion. If a record cannot be interpreted safely, leave it intact and report the gap.
