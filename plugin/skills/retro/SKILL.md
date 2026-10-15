---
name: retro
description: Maintain private retrospective findings and bounded progress, prepare recurring practices as public repository rules, and reconcile accepted promotions.
disable-model-invocation: true
---

# Agent retrospective

Run as a separate, bounded pass, manually or from an external nightly job invoking the
agent host. In Claude Code invoke `/dotbrain:retro`; in Codex invoke `$retro`. The host
owns scheduling and serialization. This skill supplies no scheduler or CLI loop runner.

Maintain `RETRO.md` in the project's private Brain, resolved through its existing wiring.
These are agent **findings**; human **lessons** remain owned by `teach-me`. Add no human
learning entries, parked concepts, checkpoint hooks, handoff steps, or session-start
injection. Invoking this skill grants no push, PR, merge, release, or publication authority.

## Stop before you start

If the private Brain or evidence sources cannot be identified, report the missing source
without creating a public substitute. If another writer owns this notebook, stop without
writing. All worktrees and external jobs share the same notebook, not per-checkout copies.
Findings never override established rules, decisions, or human-owned acceptance criteria.

## Process

### 1. Reserve the notebook and bound the pass

Acquire exclusive ownership of the resolved notebook before reading state for an update.
Use the host's per-notebook single-writer lease or an exclusive filesystem lock adjacent
to the private notebook, held through the final write. Record owner and acquisition time;
release on exit. After a crash, recover a stale lock only after verifying its owner has
stopped. A PID alone can be reused; check its creation time too. If exclusivity cannot be
established, stop. Delegates may read evidence; only this writer edits the notebook.

Read [the notebook contract](references/notebook.md) before creating or updating state.
On a first pass, declare a bounded initial range before review: use the caller's range,
or default to the latest 50 commits reachable from the selected HEAD and the last 14 days
through a fixed UTC cutoff for other sources. Record the exact selected commit IDs or
base/head, timestamps, source scopes, timezone, and excluded older history. An empty Git
repository has an empty Git range. Never imply older history was reviewed.

On later passes, retain the completed cursors and freeze proposed upper bounds before
review. Resume an interrupted pending range first. Preserve the recorded counting timezone
(default `UTC`); changing it requires recomputing all evidence dates together.

Completion: one writer owns the notebook and the exact pending range, exclusions, and
source gaps are recorded without moving any completed cursor.

### 2. Discover changed evidence

Follow the source-specific cursor protocol in the notebook contract. Compare Git reachability,
issue revisions, comment fingerprints, and selected document versions with completed state.
Use `bd list --updated-after`, per-item `updated_at`, `bd show` revision tokens, and
`bd comments <id> --json`. Include closed issues. An issue's old creation date does not
exclude its changed notes, acceptance evidence, review, or comments.

Comment changes need their own visibility check; never assume they bump the parent timestamp
or revision. Metadata enumeration and fingerprint comparison are discovery, not substantive
review. If all source versions are unchanged and no pending evidence remains, skip substantive
review and leave findings and distinct-day counts unchanged; report the checked bounds.

Report an unreachable old Git head or rewritten history as a gap, following the recovery
protocol. Report source failures and timestamp uncertainty explicitly; do not claim a complete
range when a source was unavailable. Other independently bounded sources may proceed.

Completion: each new or changed record is queued once, unchanged records are skipped, and
any uncovered range remains a recorded gap rather than a completed cursor.

### 3. Capture findings from the changed evidence

Examine commits, work and review records, active designs, and explicit human corrections
within the selected range. Focus on reworked fixes, work that should not have landed, weak
verification, and successful practices worth repeating. Local integrated work can support
an observation before public merge; a candidate alone does not prove a fix worked.

For each useful finding state its trigger, practice, reason, observations, inference, and
evidence limits. Link the actual evidence privately. Record successful practices alongside
mistakes, with the observed outcome and verification scope. Unsupported general advice is
not a finding. A record can be processed without producing a finding.

Reuse a finding by trigger and required practice, retaining its immutable `finding_id`.
Resolve source overlap to the same underlying `occurrence_id` before counting: a commit
quoted in a review and repeated in a work item is one occurrence with several source aliases.
Revisiting a commit, changed wording, and interrupted retries add no occurrence or date.
When independence is uncertain, link the corroboration and keep it uncounted with a reason.

Count distinct evidence dates in the single recorded timezone, never retrospective run dates.
Several observations on one day count once. A catch-up pass can establish several days only
from independently dated occurrences. Follow the identity and date rules in the contract.

Completion: useful changed evidence is attached to stable findings, observations and inference
are distinguishable, and every counted date is supported by a deduplicated occurrence.

### 4. Persist and checkpoint

Persist findings before advancing progress. Save the notebook atomically (temporary file and
replace while holding the lock), retaining the old completed cursors and pending range. Read
back the saved evidence identities and dates. Only then mark processed versions complete and
advance each fully processed source cursor in a second atomic save. If interrupted, resume
from the old cursor and pending range; upsert the same identities instead of appending copies.
Never checkpoint an unread page, failed query, or unprocessed record. Leave concurrently
changed records queued for a later pass rather than certifying a version not actually read.

Derive `promotion.status: eligible` when a finding has at least three distinct supported days;
otherwise use `collecting`. Preserve any later promotion state and destination already present.
This is the seam for the promotion step below: capture does not author `RULES.md`, prepare
public changes, or reconcile merges. Compact duplicated prose and already promoted entries
while preserving IDs, evidence dates, provenance, limits, and public promotion destinations.

Completion: saved findings survive a retry, completed progress covers only durable processed
evidence, and pending work and gaps remain explicit.

### 5. Prepare and reconcile public rules

Read [public rule promotion](references/promotion.md) for eligible findings and unresolved
proposals. Run this step even when discovery skipped unchanged evidence: an earlier proposal
may now have merged. Consume the saved finding identity, `evidence_dates`, `distinct_days`,
and `promotion` state; do not recapture evidence or add recurrence for a promotion review.

Automatically prepare one standalone root `RULES.md` change after three distinct supported
days, reusing or amending equivalent rules. Apply the edit only in a clean checkout or worktree
based on the recorded target branch; otherwise persist the patch privately. Never edit rules
on an unrelated feature branch. Reconcile earlier proposals with bounded read-only
merge evidence. Persist promotion history in the same private notebook under the existing
exclusive ownership and atomic-save protocol. Promotion never advances capture cursors.

Completion: each eligible finding has one prepared or reused rule, or an explicit private
hold; pending proposals remain pending until verified target-branch acceptance, and adopted
rules have a public destination and adoption date with private merge provenance.

### 6. Report

Report the completed range per source, new or updated finding IDs, supported distinct-day
counts, skipped unchanged sources, exclusions, pending work, and gaps. State whether the pass
completed or stopped partially. Release exclusive ownership. Keep evidence and notebook
contents private; do not create a second diary or public evidence store.
Include prepared public destinations, unchanged proposals, promotion holds, and reconciled
adoptions. Distinguish a prepared local change from repository acceptance.
