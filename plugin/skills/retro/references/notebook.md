# Private notebook contract

Keep state and findings together in the private Brain's `RETRO.md`. Create it only when
running this skill. Use a YAML fenced block for progress and a YAML block per finding,
with optional explanatory prose. The following empty shape is a format example, not a
seeded project file. Version 1 consumers preserve unknown fields.

```yaml
schema: 1
timezone: UTC
progress:
  scope: {}                 # repository/tracker identities, selected refs and document paths
  initial_range: {}         # exact bounds and exclusions; immutable coverage declaration
  completed:
    git: null               # repository identity, selected ref, full head OID
    beads: null             # tracker identity, through timestamp, items map
    documents: {}           # source identity -> processed content fingerprint
  pending: null             # fixed bounds, discovered versions, remaining IDs, processed IDs
  gaps: []                  # source, missing range, reason, resolution or still open
```

```yaml
finding_id: f-0001
trigger: ""
practice: ""
reason: ""
kind: mistake              # mistake | success | mixed
observations: []           # facts linked to occurrence IDs
inference: ""
limits: []
evidence: []               # occurrence records defined below
evidence_dates: []         # sorted unique supported YYYY-MM-DD dates, derived from evidence
distinct_days: 0           # derived; never increment a counter on each run
promotion:
  status: collecting       # collecting | eligible | pending | promoted
  destination: null        # accepted public RULES.md section; null until verified
  adopted_at: null         # capture never asserts public adoption
```

## Finding and evidence identity

Assign a notebook-local immutable `finding_id` once. Match existing findings by semantic
trigger and required practice, not wording, source, date, or current title. Amend the same
finding when its explanation improves. If duplicates are consolidated, preserve the retired
ID as an alias to the surviving ID so a later promotion consumer can resolve it.

An evidence record has these fields:

- `occurrence_id`: immutable ID for one underlying event, reused across findings and sources.
- `event_key`: canonical origin identity: repository identity + full commit OID + event anchor,
  or tracker identity + issue/comment ID + event anchor, or document identity + stable event
  anchor. An anchor distinguishes separate demonstrated events within a record, not edits.
- `aliases`: all equivalent source record keys, with the version/fingerprint actually read
  and private locator. Consult aliases across the notebook before assigning an occurrence ID.
- `occurred_at`: evidence-supported event timestamp with offset, or null with an explicit gap.
- `date`: date after converting `occurred_at` to the notebook timezone, or null.
- `counted`: boolean, plus `count_reason` for uncertainty, corroboration, or exclusion.
- `observation`, `outcome`, `limits`: the fact, demonstrated result, and uncertainty.

A **source record key** identifies a commit, issue, comment, or document independently of its
version. A **source version** is an OID, opaque `bd show` revision string, or deterministic
content fingerprint. Keep issue `updated_at` separately. Changing a version makes a record
eligible for review, not a new occurrence. Use stable canonical serialization (sorted JSON
object keys, stable list order) and SHA-256 for fingerprints; omit transport-only fields.
Comment fingerprints include comment ID, author, body, created time and any updated time.
An aggregate comments fingerprint sorts comments by stable ID and includes every record
fingerprint, so additions, edits, and deletions are visible.

Prefer the original event as the canonical origin. A review quoting a commit and an issue
summarizing that review are aliases of that event, even when published on different days.
An independent later test or failure is a separate event only when evidence establishes its
identity and occurrence time. Similar text alone proves neither sameness nor independence.
Record unresolved overlap as uncounted corroboration rather than inventing another day.
Rewritten commits describing the same event retain its occurrence ID and gain OID aliases.

Use the original event's date, not the dates of copied reports, edits, processing, or retries.
For a commit-origin event use its committer timestamp unless stronger dated evidence locates
the actual event. A review/comment creation time dates an original observation, not a quoted
event. Issue `updated_at` and document modification time are discovery cursors, not proof of
recurrence. A body edit corrects an existing occurrence; it does not append today's date.
If the source corrects an event timestamp, replace the old date and recompute derived dates.
Undated or ambiguous evidence remains useful but uncounted. Contradictory evidence updates
the limits and counted status; preserve provenance even when retracting support.

Compute `evidence_dates` as the sorted set of dates of counted, independent occurrence IDs
in the finding; compute `distinct_days` as its size. Several IDs on the same day count once.
Recompute after alias consolidation or correction. Preserve the recorded timezone; never mix
local machine dates with UTC. Three supported dates make `promotion.status` eligible for a
later pass; eligibility grants no new rule authority or public adoption.

## Promotion history

[Public rule promotion](promotion.md) owns preparation and merge reconciliation. Capture
continues to derive `collecting`/`eligible` and preserves `pending`/`promoted` and all history.
Eligibility is not adoption. Pending includes a prepared local change, an open or approved
PR, a closed unmerged PR, and reuse awaiting acceptance evidence. `destination` and `adopted_at`
remain null until acceptance is verified. A hold records its reason without discarding state.

Extend `promotion` when first preparing a proposal; preserve unknown fields on every save:

- `proposal_id`: immutable notebook-local identity, reused across retries, revisions, redirects,
  and findings sharing an equivalent rule. Store one canonical proposal; other findings point
  to it. Lookup by repository, target branch, and semantic trigger/practice before allocating.
- `repository`, `target_branch`, `section`: intended public destination, separate from accepted
  `destination`. Never use a local delivery branch as the acceptance target.
- `action`: `add`, `amend`, or `reuse`; `public_text` or `public_patch` holds the exact safe
  proposal; `fingerprint` identifies its canonical UTF-8 bytes. Keep previous revisions in history.
- `pr`: public URL/number when known, otherwise null. Pending does not invent delivery authority.
- `hold`: null or the private reason and missing evidence/decision; no repeated proposal on rerun.
- `history`: preparation/revision/disposition/acceptance records with `observed_at`, action,
  fingerprint, and private provenance. Acceptance includes repository, target, PR, merge OID,
  merge timestamp, inspected target OID, public section/destination, and the read-only evidence.
  Deduplicate acceptance by repository, target, PR, merge OID, and section; unchanged observations
  do not append a new history record. Closed unmerged disposition remains pending.

Reserve and persist the proposal before editing public rules. If interrupted before or after
the edit, compare the persisted text/fingerprint with the actual public section and resume
that proposal. Reconciliation updates only promotion state; it never changes occurrence IDs,
evidence dates/counts, or completed capture cursors. If later evidence retracts the threshold,
record a hold and retain the pending/adopted history; do not erase a public rule automatically.
Compaction preserves all deduplication keys, evidence provenance, accepted destinations/dates,
and proposal redirects, including when several findings reuse one rule.

## Source cursors

### Git

Record repository identity, selected ref, and full head OID, not just a timestamp. Freeze the
new head before review. For an incremental pass verify the old object exists and is an ancestor
of the new head, then enumerate `old..new` reachable commits. For the initial default enumerate
at most 50 reachable commits and store their exact OIDs, including the oldest selected boundary;
do not use commit timestamps as traversal cursors. Clock skew must not hide reachable commits.
Review relevant changes/results, not just commit subjects.

If the old head is unreachable/missing, or is not an ancestor after rewritten history, record
a history gap with both heads and reason. Keep the old completed cursor. Do not silently fall
back to all history or claim continuity. A recovery pass can declare a fresh bounded range
and explicit reset, preserving the missing range as an unresolved gap in progress and in its
report. Reuse occurrence IDs/aliases when recovered evidence overlaps previous observations.

### Beads and comments

Scope to the identified project tracker, including closed issues. Freeze a UTC cutoff `T`
at discovery start. Completed state stores `through`, and an items map of issue ID to
`updated_at`, `revision` (opaque string), `comments_fingerprint`, and per-comment fingerprints.
Pending state stores the actual source versions read and their processing dispositions.

Query `bd list --all --limit 0 --updated-after <overlap-start> --json`, with overlap-start
one second earlier than the previous `through` (or initial lower bound). This deliberately
replays timestamp boundaries: both strict and inclusive server comparisons, equal timestamps,
and subsecond precision are safe only when replay is deduplicated by source key/version.
Compare per-item `updated_at` and fetch changed candidates with `bd show <id> --json`.
Read and retain the returned revision token as a string; never order or increment it.
All pages must be read; a server-side limit or truncation is a gap, not completion.

Do not assume a comment edit changes issue `updated_at`, issue revision, or comment count.
For correctness, enumerate issue IDs with `bd list --all --limit 0 --brief --json`, then
fetch `bd comments <id> --json` for every scoped issue, including old and closed issues,
and compare aggregate and individual fingerprints. This is a metadata visibility sweep;
only changed comment records receive substantive review. It also discovers newly visible
issues. On the initial pass seed fingerprints for older comments but review only evidence
within the declared range; record the older exclusion. On later passes an edited old comment
is eligible even if its creation date predates that range. Removed records retain prior
provenance and become evidence-limit updates, never extra occurrences.

This fallback costs one comments query per scoped issue because parent-update visibility is
not guaranteed. A smaller scope must be explicit in progress and the report; never silently
omit old issues. If the sweep cannot finish within the pass budget, retain pending IDs and
resume without advancing completed Beads progress. A failed comments query is not an empty list.

Bracket issue/comment reads with `bd show` and compare revisions/updated times; compare comment
fingerprints again before checkpointing, independently of issue revision. If a source changes
during the read, retain its unprocessed version in pending and retry next pass. Records with
`updated_at > T` stay pending for the next range; don't certify them through `T`. The overlapping
next query and independent comment sweep protect same-timestamp changes. Metadata-only changes
may produce no finding but still need a processed disposition. Advance `through` to `T` only
after every in-range candidate and the entire comment sweep have durable dispositions.

### Other evidence

Name selected active designs, review sources outside Beads, and supplied human corrections
in source scope. Record stable source keys and content fingerprints, plus a real update query
or explicit bounded enumeration for each. For documents, check selected file fingerprints on
each pass and review changed content only. A newly supplied correction with no stable source
gets a persisted notebook-local source ID and fingerprint so a retry can recognize it. Correlate
copies with original evidence before counting. Do not claim coverage of unsupplied conversations
or sources without an update mechanism. Failed reads leave their old cursor and an explicit gap.

## Interrupted passes and maintenance

Pending bounds and source versions are processing state, not a diary. Persist findings and
their aliases with old completed progress first, then read back and checkpoint processed source
versions in a separate atomic replacement. A crash between saves repeats discovery but upserts
the same finding and occurrence IDs. A crash before a finding save leaves the old cursor intact.
Partial source completion must not discard the remaining pending IDs. An unchanged rerun with
no pending work compares versions and skips substantive review without changing recurrence.

Compact prose, not the deduplication ledger: preserve event keys, aliases, dates, evidence
limits, finding ID redirects, and any promotion destination/history. Never prune identities
merely because a source cursor passed them; future cross-source evidence may refer to them.
