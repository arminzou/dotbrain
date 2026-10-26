---
name: run-retro
description: Curate private retrospective findings from recent work, audit whether they improve later work, suggest repository rules, and deliver authorized rule proposals through dedicated PRs.
disable-model-invocation: true
---

# Agent retrospective

This skill exists so agents stop repeating mistakes and so the human can see when the feedback
loop goes wrong and steer it. Run it manually or from an external agent-host schedule. In Claude
Code invoke `/dotbrain:run-retro`. In Codex select this skill from the skill picker and use its
exposed name; `$run-retro` is not confirmed for plugin delivery. The host owns scheduling. This
skill supplies no scheduler or CLI loop runner.

Maintain private `RETRO.md` as plain Markdown. These are agent findings; human lessons belong
to `teach-me`. This skill is the notebook's only writer: leads record retro candidates on their
own work records at completion, and this skill curates those into findings and recovers what they
missed. Add no checkpoint hooks, handoff steps, or
session-start injection. Public auto-delivery is disabled unless explicitly enabled in private
`project.yaml`; otherwise suggest rules for the user's decision. Apply the dotbrain convention's
human gates.

## Choose the mode

- **Curate** (default; scheduled or manual): consolidate findings, recover missed ones, and
  propose interventions. Writes the notebook.
- **Audit** (only when the human asks; never scheduled): judge whether the loop improves later
  work enough to justify its cost, and recommend keep, revise, or stop. Read-only.

A manual curate run with the human present first resolves pending decisions (see
[Report](#report)); an audit only lists them.

## Stop before you start

If the private Brain or evidence sources cannot be identified, report the missing source
without creating a public substitute. Findings never override established rules, decisions, or
human-owned acceptance criteria. Manual and scheduled passes can overlap on one notebook: every
write uses [the compare-and-swap save](references/retro.md#save), never a lock.

## Curate

### 1. Bound the pass

Read [the retrospective format](references/retro.md). On first use, read current root guidance
and referenced standards, record scope, guidance links, timezone, and a curation cutoff of now,
then save, report initialization, and stop. First use reviews no history.

Require an explicitly selected contributor scope (branches/PRs) or repository scope (integration
branch); never infer ownership from authors. If scope is unset, report the missing choice without
capturing work. In repository scope, while the header has no `Rules file:` line or says
`Rules file: offered`, follow [the rules file offer](references/retro.md#rules-file-offer).

Default limit per pass: 25 changed records plus their linked evidence, or 15 minutes, whichever
comes first, unless the request sets another. With the human present, resolve pending decisions
now and save them on their own. Then read the notebook and record its hash; every later change in
this pass stays in memory until step 5.

Completion: scope is explicit, the limit is known, and the notebook hash is recorded.

### 2. Select changed records

Select work and review records changed since the saved curation cutoff, oldest update first, as
the reference describes. A lead's candidate flag write updates its bead, so new retro candidates
arrive in this selection. On each selected bead, judge every `## Retro candidate` comment that the
notebook does not cite and no later `## Retro candidate judged` comment answers, whatever its
date. Then read the other evidence: CHANGES verdicts, failed checks, rejected candidates, human corrections,
defects, and informative successes or recoveries. Commits alone are not the signal; much
correction evidence never reaches the integration branch. Include explicitly supplied incidents
regardless of date. Use commits and CI only as supporting evidence.

If nothing changed, no decision is pending, and no recorded `Proposal:` awaits reconciliation,
exit silently without rewriting the notebook.
A completion-time entry already in the notebook does not justify rereading its whole source;
follow up only on missing evidence, changed outcomes, or a concrete conflict. State discovery
limits; a date query can miss edited or unattributed evidence.

Completion: the selected records, the stopping point, and source gaps are known.

### 3. Curate findings

A finding earns an entry only if it would change a future task's decision, states when it applies
and what to do, and adds guidance beyond existing instructions or protection. Successful practices
qualify like mistakes. Merge duplicates, sharpen practices and triggers, reconcile contradictory
evidence, and retire findings already covered by `RULES.md`, tests, skill text, or structural fixes.
Leave unresolved observations in their source records. Separate observed facts from inference and
preserve limits.

Completion: each kept finding has practice, trigger, needed limits, and dated source pointers.

### 4. Suggest, deliver, and reconcile public rules

Read [promotion](references/promotion.md), even when nothing new was selected. For each finding
still unprotected, judge impact, evidence confidence, applicability, and existing protection, and
suggest the strongest intervention that fits: structure, type, check or hook, test, then rule
text. Record it as `Enforcement:` beside the finding. Suggest only: never build a check, hook, or
test, even with auto-delivery enabled.

With auto-delivery disabled or unset, keep the suggestion private and raise it as a pending
decision. Make no public edit, commit, push, or PR without proposal-specific authorization. A
scheduled run never waits for a reply.

When authorized, follow [the public rule format](references/rules.md) and the destination's
conventions. Prepare in a clean target-based checkout or worktree, never on an unrelated feature
branch. Use run-retro's own PR process and body, not the `pr` skill. Save proposal state before
each public action as promotion requires, each a compare-and-swap save against the last recorded
hash, then re-hash. If the notebook changed, write only the finding that carries the proposal, with
its proposal line, onto the fresh notebook (or the line alone when that finding is already there),
again by compare-and-swap, and abandon the rest of this pass. Reconcile
actual acceptance read-only; add `Accepted:` beside the original finding only after the acceptance
checks pass.

Completion: each unprotected finding has a suggestion, proposal, accepted rule, or clear hold.

### 5. Save

Apply [the save](references/retro.md#save) once, with every change from steps 3 and 4 and the
advanced cutoff, against the last recorded hash. If the notebook changed since then, abandon
without writing; the next run redoes the work. Advance the cutoff only past records whose changes
are in this save.

After the save succeeds, answer each candidate this pass rejected (not transferable, or already
covered) with a `## Retro candidate judged` comment on its bead, naming the candidate's time and the
reason, under the pass's own actor; count rejections under SKIPPED. A kept or merged candidate is
answered by the finding that cites it. Comments do not change a bead's update time, so the cutoff
is unaffected. Never remove a `dotbrain_retro` flag. A failed or abandoned run loses nothing and
skips no records; a crash before the rejection comments re-offers those candidates once.

Completion: the notebook and cutoff changed together, or not at all.

## Audit

Write nothing persistent. The human chooses the scope or period. Inspect a
bounded sample of assignments, execution records, review findings, and verification evidence. The
notebook names the practices under evaluation; its own claims cannot establish their effect.

Report which preparations carried an applicable finding, which findings influenced later work,
later CHANGES findings that repeat a supplied practice's failure, missed or redundant findings,
unnecessary constraints, and curation and closeout cost. Distinguish a missed lookup, a delivered
but ignored practice, and an inadequate practice. Judge evidence quality, transfer, cost, and harm,
not a count: one well-evidenced case can expose harmful guidance; several similar or already
protected tasks may prove little. Insufficient evidence is inconclusive, with the specific gap.

A delivered practice with no visible effect does not by itself justify stopping the operation,
and no relevant opportunity leaves benefit unknown rather than disproved. An early audit can still
expose overhead or delivery failures before effectiveness is assessable.

Recommend at the right level: retire or revise one finding, revise delivery, or keep or stop
recurring curation. Retiring public rules or enforcement follows normal authorization.

## Report

Report only what is worth human attention: changed or retired findings, suggestions, pending
decisions, a run that hit its limit or could not read a required source, or a stuck cutoff. A quiet
run and a single failed run stay silent; the next run repeats the work. Follow
[the report format](references/retro.md#report-format): plain language, decisions first, within
about 25 lines.

Each item that needs the human is a decision record stored as a `Pending:` line beside its finding:
one question, two to four options, the recommended option with a one-line reason, an evidence
pointer, and what happens if it goes unanswered. Silence authorizes nothing; an unanswered item stays deferred and is raised again only on
new evidence. An answer authorizes only the chosen option, within existing delivery gates.

When the human is present, resolve pending decisions first through the runtime's native question
dialog (in Claude Code, `AskUserQuestion` with the recommended option first and marked), or as
numbered text where no dialog exists. Record each answer beside its finding, remove its `Pending:`
line, and save. Distinguish a prepared local change, a delivered PR, and repository acceptance.
Keep private evidence out of public delivery text.
