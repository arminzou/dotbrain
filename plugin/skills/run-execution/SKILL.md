---
name: run-execution
description: Carries out one work item or a finite batch from the private work graph — selects, dispatches workers, integrates, checks, repairs within limits, closes through manage-work-graph, and escalates or recovers. Use when asked to do, implement, or work an item, a set of items, or an epic's ready work, including requests to dispatch dotbrain workers one after another or in parallel, or via /dotbrain:run-execution. NOT for filing or reshaping work items (manage-work-graph), a design-level automation handoff (iterate-design), or independent review (review-gate).
---

# Run Execution

Run one work item by default, or an explicit finite batch of item IDs. A plain action
request starts this skill; spawning another agent is optional. The lead may be the sole
writer and assignee, or delegate to one writer. Both are sequential execution.
Read-only agents do not change execution mode.
The HITL workflow returns to the human after each bounded execution. The handoff
workflow chains executions through iterate-design's approved contract.

**Read [parallel execution](references/parallel-execution.md) before choosing or
dispatching more than one concurrent writing worker, and before a replacement worker
starts.** It owns capacity, isolation, group integration, containment, and replacement rules.

The work graph and closure rules belong to [manage-work-graph](../manage-work-graph/SKILL.md).
The handoff loop and its stop scopes belong to [iterate-design](../iterate-design/SKILL.md).

Workers use the lead's runtime unless the human explicitly asks for another, in the request
or in a project rule they wrote. Never change assigned runtime, scope, or checks on your own:
ask, or stop blocked in an autonomous run. Before dispatch, read the runtime reference of the
lead and of each worker runtime, and the worker's again before fix rounds, cancellation, or
recovery: [Claude Code](references/claude-code.md), [Codex](references/codex.md), or lead-only
[Hermes](references/hermes.md), [OpenCode](references/opencode.md), [Pi](references/pi.md),
[Cursor](references/cursor.md). They supply mechanisms; this skill's contract governs every
runtime. Prefer native subagents when runtimes match. Record any uncovered mechanism chosen by
judgment so a fix round or takeover can repeat it.

Never spawn an agent only to check a checkpoint. The writer runs its own checkpoint
checks: the tests its change affects. The full suite and any other machine-wide check is a
gate check, run once per integrated group head before promotion; reviewers do not
run it. The lead runs gate checks unless the caller names a verifier, at most one;
iterate-design reserves its verifier for the once-only in-loop gate. Spawn a reviewer
for item review. Keep exploration that feeds a design in the session that will use it.

Both workflows run on a dedicated branch and land through a review surface: a PR, or the branch
diff where the project hosts no PRs. At the first HITL bounded execution, propose the branch
and its base: an unmerged branch only when the work depends on it, else a sibling on the shared
base; one branch may span several bounded executions. Parallel workers integrate into that branch,
never into `main`. Ask before pushing or opening a PR in the HITL workflow. Apply the
convention's human gates. Local HITL landing requires explicit human instruction, recorded by the lead;
it is never the default.

## Select and work

Fix the item set at invocation. Readiness filters it; unrelated ready work never expands
it. A set may include waiting dependents. Dispatch only after prerequisite acceptance
and closure, with a base containing its accepted result and human gates resolved.
Establish checks, retry limits, capacity, and overall limits before work starts.
Before implementation or dispatch, search `.brain/RETRO.md` once for the task or related batch,
by practice and trigger. Pass matching practices and limits through assignment Constraints or
review inputs; source pointers stay with the lead unless the recipient needs that evidence.
A sole writer keeps them in its own task context. Reuse them through related dispatches, reviews,
and repair rounds; search again only for a new area or relevant new evidence. No match needs no
note.
For epic scope use `bd swarm validate <epic>` and `bd swarm status <epic>`, never
`bd swarm create`. Keep live assignments, pending joins, and next steps in this session.

Stop for missing authorized scope or required checks. Exclude `learn:` beads.
Keep human-gated items in scope and their dependents waiting. A missing required
capability blocks execution: worktree isolation for concurrent writers, a distinct Beads
actor per worker, or an independent reviewer when review is required. Stop and report;
never weaken the contract to fit the runtime. If only optional parallelism is missing,
report the serial fallback before continuing, keeping scope, isolation, checks, and gates.

At most one active writer owns an item. Delegated workers return
candidates, checks, discoveries, and design learning. Apply manage-work-graph's writer
permissions and actor rules. Worker startup is defined only
in the worker role: [`dotbrain:worker`](../../agents/worker.md) in Claude Code, the
`dotbrain-worker` agent in Codex. An unwired linked
worktree needs no tracker preparation. Runtimes start worktrees from different commits, so
never rely on where one began.

For code work, keep the delivery branch at its last accepted revision. Work and repairs
stay on an isolated candidate branch even with one writer; the sole writer may use the
lead's checkout. Preserve existing unaccepted changes as a candidate. If an accepted
delivery head cannot be safely established, hold integration and report instead of
resetting or rewriting it. For other work, name the accepted artifact and target.
Use short branch slugs without work-item IDs: branch names reach public history.

After passing writer checks, review and run combined checks against the candidate head.
Only after
required review, checks, member acceptance, and human gates pass at that revision,
promote with `git merge --ff-only <candidate-branch>` and confirm the delivery head
equals it. Then set `dotbrain_phase: verified` and apply native closure through
manage-work-graph. A candidate alone never closes an item or releases dependents.
For multi-worker integration use the parallel reference's group procedure.

Before applying closure, and when an accepted batch or integration group completes, decide
whether the outcome supports a transferable practice. Evidence stays in the work and review
records. A practice earns a candidate only if it would change another task's decision, states
when it applies and what to do, and adds guidance beyond existing instructions, tests, or
structure; check `RETRO.md` for a duplicate first. Record it as a `## Retro candidate` comment
(practice, when, limit, evidence) on the item, or on the epic for a batch or integration practice,
then flag that bead with
`bd update <id> --metadata '{"dotbrain_retro":"<UTC now>"}' --actor <lead> --json --quiet`, a new time for every
candidate. Never write
`RETRO.md`; `run-retro` curates flagged candidates. Never delay closure for it. No candidate,
"nothing learned" note, report, agent call, or `run-retro` invocation is required.

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
acceptance criteria, affected consumers, and interactions, and pass that boundary, the review
number and round, the reviewer's Beads actor, and each item's acceptance criteria in the review
request. Before dispatch, create the reviewer's checkout with `git worktree add --detach <path>
<head>` and point the reviewer at it without runtime isolation, never at the lead's checkout;
remove it with `git worktree remove` after recording the verdict. The reviewer records its report
on every boundary item and returns an index; the lead confirms and routes it as
[the execution record](references/execution-record.md) specifies.
Item and integration reviews never get a batch review bead.

### Review verdicts

Return `CHANGES` for unmet acceptance or a `blocker` or `high` regression caused by the reviewed
changes, including symptoms in unchanged consumers or interactions. Return `APPROVE` with
`medium` or `low` findings and unrelated existing defects; the lead files those as discovered
work for a later bounded execution. Missing evidence is a gap, never a verified claim; missing
coverage is a gap, never acceptance.

A change-caused failure in automatic behavior that goes unreported, or leaves state
that blocks later runs, defaults to `high` in every review unless the design explicitly
accepts that failure mode.

On `CHANGES`, resume the original writing worker using the worker runtime's reference. The lead
sets `dotbrain_phase` to `working` and appends
`## Dispatched: <worker actor> in <checkout> on <branch> @ <base> (fix round <n>)` with the
consolidated assignment and what changed since the last round; the resume message carries both
and cites the `Review` comment for the findings. The resumed worker does not touch its claim. When the lead is the sole writer, it repairs its own
work; a delegated sequential worker is resumed like a parallel worker. If the worker cannot
resume, load [the replacement rules](references/parallel-execution.md#claim-moves-and-replacements).
The same reviewer re-reviews its earlier findings and the fix diff; a newly spotted `blocker`
still counts. Each `CHANGES` is a failed check on the `item-review` checkpoint in
`dotbrain_attempts`, which keeps a separate streak per checkpoint: a worker's passing checks
during a fix round do not reset it. Only an `APPROVE` ends that streak. Three consecutive `CHANGES` block the item
through the retry-exhaustion rules; neither a replacement nor a new reviewer resets the count.

A conflict rebase does not count toward the `CHANGES` cap.
Any changed patch or integration context affecting acceptance or review/check coverage, including
a conflict rebase or integrated-check repair, needs refreshed evidence before closure. An earlier
`APPROVE` does not cover a stale revision. No item closes with an unreviewed behavior change.

Acceptance/UAT records revision, environment, agreed journeys, actual checks/results,
and gaps, including [evidence kinds and any static-only exemption](references/execution-record.md#integration-groups-and-recovery)
in every `Accepted` record. An unexercised journey never passes or automatically becomes a request for
human checking. Required UAT with failed, missing, or stale evidence holds affected work;
investigate and repair within remaining limits. Record every finding's disposition: blocking
findings resolved; others applied, filed with follow-up IDs, or declined with reasons.

## Worker assignment

Every delegated writing worker receives, in its runtime message, the labelled assignment that
[the worker role](../../agents/worker.md#the-assignment) defines (the same section of the
`dotbrain-worker` agent in Codex), with every label in order;
reviewer requests keep their own inputs. The worker's actor follows manage-work-graph's actor
rules. Make the assignment self-contained: settled constraints and exact source sections with
enough context to resolve conflicts, not the lead's conversation or whole workflow documents.
Omit only duplicated role defaults and the lead's Beads actor. The lead loads `run-execution`'s dispatch,
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
finishes, and record `Dispatched` with the full assignment as
[the execution record](references/execution-record.md#comment-headers) specifies. Workers and
reviewers launch with full access; their role definitions, not runtime configuration, keep them
within their roles. If a runtime can launch only in the foreground, record `Dispatched` before launching,
naming the branch and base, and add the checkout to the `work` artifact once the worker reports it.

A user-launched session in a worktree attaches with explicit `dotbrain wire` and leads its own execution.

## Execution record

Keep recoverable facts on each existing bead, without execution-only or batch-anchor
beads. Use native status, assignee, dependencies, flat execution metadata and headed
append-only comments as specified in [execution-record.md](references/execution-record.md).

## Failure, cancellation, and resume

Apply [iterate-design's stop scopes](../iterate-design/SKILL.md#stop-scopes) in either workflow.
Unless the assignment names another limit, an item blocks after 3 consecutive failed checks on one checkpoint, 3 consecutive
item-review `CHANGES`, or a human gate. Record `Blocked`, add `human`, keep it open,
and report the attempt trail, waiting dependents, remaining uncertainty, and a concrete
decision with a recommendation. Missing results never pass. Keep blocked items in scope.
Apply the convention's human decision and hard-stop invariants; record any authorized
new limit without resetting history. For independent work and failed groups, apply the
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

Within approved authority, apply the convention's human gates and manage-work-graph's
closure boundary. Report to the human in one table with exactly one row per item in the fixed set:
item, status, accepted revision, review verdict, and next step or blocker; no raw worker output.
Then list preserved artifacts, discovered work, and design learning.
