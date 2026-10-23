---
name: run-execution
description: Carries out one work item or a finite batch from the private work graph — selects, dispatches workers, integrates, checks, repairs within limits, closes through manage-work-graph, and escalates or recovers. Use when asked to do, implement, or work an item, a set of items, or an epic's ready work, or via /dotbrain:run-execution. NOT for filing or reshaping work items (manage-work-graph), a design-level automation handoff (iterate-design), or independent review (review-gate).
---

# Run Execution

Run one work item by default, or an explicit finite batch of item IDs. A plain action
request starts this skill; spawning another agent is optional. The lead may be the sole
writer and assignee, or delegate to one writer. Both are sequential execution.
Read-only agents do not change execution mode.
The HITL workflow returns to the human after each bounded execution. The handoff
workflow chains executions through iterate-design's approved contract.

**Before a second writing worker starts, or before a replacement worker starts, read
[parallel execution](references/parallel-execution.md).** It owns capacity, isolation,
group integration, completion handling, containment, and replacement rules.

The work graph and closure rules belong to [manage-work-graph](../manage-work-graph/SKILL.md).
The handoff loop and its stop scopes belong to [iterate-design](../iterate-design/SKILL.md).

Workers use the lead's runtime unless the human requests another in the request or a
project rule. Never change assigned runtime, scope, or checks on your own: ask, or stop
blocked in an autonomous run. Before dispatch, fix rounds, cancellation, or recovery,
read the affected runtime's mechanism: [Claude Code](references/claude-code.md),
[Codex](references/codex.md), or lead-only [Hermes](references/hermes.md),
[OpenCode](references/opencode.md), [Pi](references/pi.md), [Cursor](references/cursor.md).
Prefer native subagents when runtimes match. Record any uncovered mechanism chosen by
judgment so a fix round or takeover can repeat it.

Never spawn an agent only to check a checkpoint. The writer runs its own checkpoint
checks. Spawn the verifier for the once-only gate, at most one verifier; spawn a reviewer
for item review. Keep exploration that feeds a design in the session that will use it.

Both workflows run on a dedicated branch and land through a review surface: a PR, or the branch
diff where the project hosts no PRs. At the first HITL bounded execution, propose the branch
and its base: an unmerged branch only when the work depends on it, else a sibling on the shared
base; one branch may span several bounded executions. Parallel workers integrate into that branch,
never into `main`. Ask before pushing or opening a PR in the HITL workflow. Merge stays
human-owned. Local HITL landing requires explicit human instruction, recorded by the lead;
it is never the default.

## Select and work

Fix the item set at invocation. Readiness filters it; unrelated ready work never expands
it. A set may include waiting dependents. Dispatch only after prerequisite acceptance
and closure, with a base containing its accepted result and human gates resolved.
Establish checks, retry limits, capacity, and overall limits before work starts.
For epic scope use `bd swarm validate <epic>` and `bd swarm status <epic>`, never
`bd swarm create`. Keep live assignments, pending joins, and next steps in this session.

Stop for missing authorized scope or required checks. Exclude `learn:` beads.
Keep human-gated items in scope and their dependents waiting. Missing required
capabilities block execution; optional parallelism may fall back to serial execution
after reporting it, without weakening scope, checks, isolation, or gates.

At most one active writer owns an item. Shape concurrent parts through manage-work-graph
before execution, preserving criteria and finite limits. Delegated workers return
candidates, checks, discoveries, and design learning; the lead records them and alone
edits the design, work graph, and execution metadata. Worker startup is defined only
in the [worker role](../../agents/worker.md) and its Codex counterpart.

For code work, keep the delivery branch at its last accepted revision. Work and repairs
stay on an isolated candidate branch even with one writer; the sole writer may use the
lead's checkout. Preserve existing unaccepted changes as a candidate. If an accepted
delivery head cannot be safely established, hold integration and report instead of
resetting or rewriting it. For other work, name the accepted artifact and target.
Use short branch slugs without work-item IDs: branch names reach public history.

After passing writer checks, review and run combined checks against the candidate head.
The lead runs these checks; reserve the verifier for the once-only gate. Only after
required review, checks, member acceptance, and human gates pass at that revision,
promote with `git merge --ff-only <candidate-branch>` and confirm the delivery head
equals it. Then set `dotbrain_phase: verified` and apply native closure through
manage-work-graph. A candidate alone never closes an item or releases dependents.
For multi-worker integration use the parallel reference's group procedure.

Remove only closed items' merged branches and clean worktrees with `git branch -d`
and `git worktree remove`, including runtime-created branches and accepted candidate
branches. Never force cleanup. Report dirty or unmerged artifacts and preserve them.
Repairs stay inside scope and limits. Discoveries become facts or later work items;
they never silently join this execution.

## Item review and acceptance

Every work item's behavior change gets required independent `code` review before closure, with
combined checks and acceptance coverage for every member at the exact integrated revision.
Behavior includes code, tests,
build or CI config, and instructions agents execute: skills, prompts, and agent definitions.
Changes confined to human-facing prose docs, comments, formatting, or generated output are exempt;
the lead records `## Review skipped: <reason>` on the work item.

In the HITL workflow only, the lead may ask whether a small behavior change needs review. The
prompt includes the diffstat, the behavior changed, and the lead's recommendation. Keep the item
open until the human answers. Record a decline as
`## Review skipped: declined by human — <reason>`. Standing answers hold until the human changes
them. The handoff workflow never asks; it reviews every behavior change. An explicit human review
override remains binding.

Use a reviewer agent that authored none of the reviewed change. The lead never reviews changes
it authored. Fix the boundary at the group base and exact integrated head, included items,
acceptance criteria, affected consumers, and interactions. The reviewer returns its complete
structured report without tracker writes; the lead records it on member beads before notifying
workers, following [the execution record](references/execution-record.md). Preserve reviewer
identity, revision references, acceptance coverage, per-item verdicts, findings, and evidence gaps.
Assign each cross-item finding to one responsible original worker and link the finding from every
affected member. Item and integration reviews never get a batch review bead.

Return `CHANGES` for unmet acceptance or a `blocker` or `high` regression caused by the reviewed
changes, including symptoms in unchanged consumers or interactions. Return `APPROVE` with
`medium` or `low` findings and unrelated existing defects; the lead files those as discovered
work for a later bounded execution. Missing coverage is a gap, never acceptance.

On `CHANGES`, resume the same writing worker to fix its candidate using the worker runtime's
reference. The lead sets `dotbrain_phase` to `working` and
appends `## Dispatched: <worker actor> in <checkout> on <branch> @ <base> (fix round <n>)`.
The resumed worker does not touch its claim. When the lead is the sole writer, it repairs its own
work; a delegated sequential worker is resumed like a parallel worker. If the worker cannot
resume, load [the replacement rules](references/parallel-execution.md#claim-moves-and-replacements).
The same reviewer re-reviews its earlier findings and the fix diff; a newly spotted `blocker`
still counts. Each `CHANGES` is a failed check on the `item-review` checkpoint in
`dotbrain_attempts`, which keeps a separate streak per checkpoint: a worker's passing checks
during a fix round do not reset it. Only an `APPROVE` ends that streak. Three consecutive `CHANGES` block the item
through the retry-exhaustion rules; neither a replacement nor a new reviewer resets the count.

Both execution modes: passing worker checks, candidate, provisional integration, coherent group
review and combined checks, member acceptance and resolved human gates, close as `verified`,
clean up, release dependents. A conflict rebase does not count toward the `CHANGES` cap.
Any changed patch or integration context affecting acceptance or review/check coverage, including
a conflict rebase or integrated-check repair, needs refreshed evidence before closure. An earlier
`APPROVE` does not cover a stale revision. No item closes with an unreviewed behavior change.

## Worker assignment

Every delegated worker receives a compact assignment in its runtime message:

- work-item IDs and the assigned operation
- the worker's Beads actor, passed as `--actor <worker-actor>` on every `bd` write; without it the
  actor is the shared Git user, and a repeated claim by the same actor succeeds silently
- project rules, acceptance criteria, task limits, permission boundaries, and named skills
- allowed actions and file or resource ownership, behavioral responsibility, and known file overlap
- checkout, item branch, and base revision, where applicable
- relevant authority text or precise source sections, with source identity and enough context
  to resolve conflicts; required project rules still apply
- required checks and the artifacts, evidence, and blockers to return
- any override of a role default, including retry, escalation, or commit-convention overrides

Make the assignment self-contained: include settled constraints and exact authority sections,
not the lead's conversation or whole workflow documents. Omit only duplicated role defaults and
the lead's Beads actor; keep the worker's own actor and every assignment-specific override.
The worker's role supplies the default retry/escalation rules and commit-convention fallback.
The lead loads `run-execution`'s dispatch,
integration, and recovery references;
workers load their role contract, project rules, and task-relevant sections and skills. Supply known
tool names and commands; discover capabilities or read subcommand help only when something is
missing or fails. Keep local code questions in the lead or built-in explorer; use the researcher
when outside sources must be reconciled with project knowledge.

Inherit the configured model unless the user explicitly requests a different model. Record the
user-requested model or that the model inherits the runtime setting in the assignment.
Packaged definitions keep their role effort and no model pin.
Runtime references own history controls and how to apply model and effort settings.

Launch each delegated writing worker in the background, so the launch returns before the worker
finishes. As soon as the runtime identifies the worker, record `## Dispatched` with its checkout,
branch, and base, with the worker's runtime and its agent or session ID in the comment body, before waiting on the
worker. A record written after the worker returns leaves no trace of a running worker if the lead
stops, and a fix round or takeover needs that ID. If a runtime can launch only in the foreground,
record `Dispatched` before launching, naming the branch and base, and add the checkout to the
`work` artifact once the worker reports it.

Claims, actors, and native closure follow manage-work-graph. A user-launched session
in a worktree attaches with explicit `dotbrain wire` and leads its own execution.

## Execution record

Keep recoverable facts on each existing bead, without execution-only or batch-anchor
beads. Use native status, assignee, dependencies, flat execution metadata and headed
append-only comments as specified in [execution-record.md](references/execution-record.md).

## Failure, cancellation, and resume

An item blocks after 3 consecutive failed checks on one checkpoint, 3 consecutive
item-review `CHANGES`, or a human gate. Record `Blocked`, add `human`, keep it open,
and report the attempt trail, waiting dependents, remaining uncertainty, and a concrete
decision with a recommendation. Missing results never pass. Keep blocked items in scope.
Only the human authorizes more attempts or changed criteria; retain the history and
record the new decision and limit. For independent work and failed groups, apply the
parallel reference's containment rules before continuing.

Cancellation stops dispatch and integration. Ask workers to stop, preserve unfinished
changes and worktrees, record `Cancelled`, and leave items open. Report uncertain
termination before any claim release. Cancellation authorizes no cleanup, reversal,
or design abandonment.

Only a user-requested resume establishes a replacement lead. First reconcile active
workers, claims, records, artifacts, and target revision. Keep scope, checks, limits,
attempt counts, and pending gates. Resume original workers within remaining limits;
load the parallel reference before any replacement. Resume never resets a streak.
Surface unknown ownership or limits. Reconstruct item-level next steps rather than
promising to restore the former batch or choosing a different one.

## Completion

Within approved authority, implement, commit, integrate, check/UAT, shape tasks, and
close accepted work without routine sign-off. Stricter instructions still bind.
Follow manage-work-graph's closure boundary. Return closed items, open items and their
blockers/gates/cancellation, preserved artifacts, discovered work, and design learning.
