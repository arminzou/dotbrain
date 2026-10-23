---
name: run-retro
description: Maintain private retrospective findings, suggest recurring repository rules, and deliver authorized rule proposals through dedicated PRs.
disable-model-invocation: true
---

# Agent retrospective

Run as a separate bounded pass, manually or from an external nightly job invoking the agent
host. In Claude Code invoke `/dotbrain:run-retro`. In Codex select this skill from the skill picker
and use its exposed name; `$run-retro` is not confirmed for plugin delivery. The host owns
scheduling and serialization. This skill supplies no scheduler or CLI loop runner.

Maintain private `RETRO.md` as plain Markdown. These are agent findings; human lessons belong
to `teach-me`. Add no human learning entries, checkpoint hooks, handoff steps, or session-start
injection. Public auto-delivery is disabled unless explicitly enabled in private `project.yaml`.
Otherwise suggest rules and destinations for the user's decision. Enabled delivery or explicit
proposal authorization permits its dedicated commit/push/PR. Apply the dotbrain convention's human gates.

## Stop before you start

If the private Brain or evidence sources cannot be identified, report the missing source
without creating a public substitute. If another writer owns the notebook, stop without
writing. All worktrees and external jobs share the same notebook. Findings never override
established rules, decisions, or human-owned acceptance criteria.

## Process

### 1. Reserve and bound the pass

Acquire exclusive ownership before reading for an update. Use the host's per-notebook lease
or an exclusive adjacent `RETRO.md.lock`, held through the final save. Exclude that lock and
`RETRO.md.tmp.*` in the private repository's local Git exclude file before creating them.
Record the owner and acquisition time. Recover a stale lock only after verifying its owner
has stopped (check process creation time as well as PID). Only this writer edits the notebook.

Read [the retrospective format](references/retro.md). On first use, read current root guidance
and referenced standards, establish current HEAD as the baseline, and record scope, guidance
links, initialization time, timezone, exclusions, and `Unfinished: none`. No history audit or
findings are created just by reading standards. Save and report initialization, then stop.
An explicitly requested historical pass is separate and does not move the forward boundary.

Reuse existing shared progress across worktrees and machines. Require an explicitly selected
contributor scope (branches/PRs) or repository scope (integration branch); never infer ownership
from authors or silently include all upstream commits. If scope is unset, report the missing
choice without capturing work. In repository scope, while the notebook header has no
`Rules file:` line or says `Rules file: offered`, follow [the rules file offer](references/retro.md),
including on first use; contributor scope never creates a public file. On later passes, resume
recorded unfinished work or freeze the next source head/cutoff and review forward from its
saved boundary. Record exclusions and gaps; never imply excluded older history was reviewed or
reset a mismatching boundary automatically.

Completion: one writer owns the notebook and the intended scope is explicit.

### 2. Review scoped evidence

Use the previous reviewed Git boundary when valid; follow the reference's ancestry and gap
rules. Inspect scoped commits, relevant work/review records (including closed items), active
designs, and supplied human corrections. Review linked records and explicitly requested older
evidence without a whole-tracker comment sweep. State coverage limits; parent timestamps do
not guarantee discovery of comment edits. If there is no new evidence, skip substantive review
and leave recurrence unchanged. Source failures remain gaps while independent sources proceed.
Read current guidance relevant to that work, including scoped instructions; baseline links
do not freeze standards. A proposed practice cannot override newer accepted rules.

Focus on reworked fixes, work that should not have landed, weak verification, and successful
practices worth repeating. Local integrated work can support an observation before public
merge; a candidate alone does not prove a fix worked.

Completion: the reviewed range, useful observations, and unresolved gaps are known.

### 3. Update findings

Write a bold practice, short reason, dated evidence, and limits. Record successful practices
alongside mistakes with `Done right`. Separate observed facts from inference. Reuse an entry
by situation and practice; copied sources and retries add no occurrence or date. Count distinct
evidence dates in the recorded timezone, never run dates. Uncertain evidence remains uncounted.
Update `Seen n× (dates)` from the supported dates. Three distinct supported dates establish
eligibility, not adoption. Preserve pending PRs, accepted links, and unresolved holds.

Completion: useful findings have traceable evidence and supported counts, without duplicate entries.

### 4. Save progress

Save findings before advancing the reviewed boundary. Write to an adjacent
`RETRO.md.tmp.<owner>.<nonce>` and atomically replace on the same filesystem, retaining the old
progress and unfinished range. Read back, then save the completed boundary and remaining work.
Never advance past unread or failed evidence. On interruption, resume the named range and
compare existing entries before appending. Compact repeated prose without discarding meaningful
evidence, supported dates, limits, or public links. No duplicate YAML ledger or sidecar is needed.

Completion: findings are durable and progress describes only saved, actually reviewed work.

### 5. Suggest, deliver, and reconcile public rules

Read [promotion](references/promotion.md) for eligible findings and pending proposals, even
when capture found no new evidence. After three distinct supported days, discover repository
guidance and suggest an appropriate file, practice, rationale, and review check. Also suggest
the strongest mechanical enforcement that would work (structure, type, check or hook, test),
recorded as `Enforcement:`; rule text is the fallback. Suggest only: never build the check,
even with auto-delivery enabled.

With auto-delivery disabled/unset, keep the suggestion private and report it for the user's
decision. Make no public edit, commit, push, or PR without proposal-specific authorization.
A nightly run leaves the suggestion without waiting interactively. Do not enable delivery
or select fallback destinations automatically.

When authorized, follow [the public rule format](references/rules.md) and the destination's
conventions. Prepare in a clean target-based checkout/worktree; never on an unrelated feature
branch. Use run-retro's own PR process and body, not the `pr` skill. Several findings can share a
proposal; related rules may share a PR. Reconcile actual acceptance read-only, without changing
capture dates or coverage. After acceptance checks, add `Accepted:` beside the original finding;
keep it in its work-area section.

Completion: each eligible finding has a suggestion, proposal, accepted rule, or clear hold, and an
`Enforcement:` line;
authorized delivery has a confirmed PR or recorded blocker.

### 6. Report

Report the reviewed range, finding practices and supported counts, exclusions, unfinished work,
source gaps, suggestions, enforcement suggestions, PR URLs, and accepted destinations. Distinguish a prepared local change,
a delivered PR, and repository acceptance. Keep private evidence out of public delivery text.
Release ownership on exit, including partial failure. Do not create a second diary.
