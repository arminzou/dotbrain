---
name: run-execution
description: Carries out one work item or a finite batch from the private work graph — selects, dispatches workers, integrates, checks, repairs within limits, closes through manage-work-graph, and escalates or recovers. Use when asked to do, implement, or work an item, a set of items, or an epic's ready work, or via /dotbrain:run-execution. NOT for filing or reshaping work items (manage-work-graph), a design-level automation handoff (iterate-design), or independent review (review-gate).
---

# Run Execution

Run one bounded execution: one work item by default, or an explicit finite batch of item IDs. The
work graph says what depends on what; this skill owns the **execution graph** — how an agent team
carries out the fixed item set — and each item's **execution record**. Graph maintenance and
closure rules stay with [`manage-work-graph`](../manage-work-graph/SKILL.md).

A plain action request ("do X", "work the ready items under this epic") starts this skill.
Calling it does not require spawning another agent.

Before worker preparation or dispatch, read the applicable runtime reference:
[Claude Code](references/claude-code.md) or [Codex](references/codex.md). Read it again before
runtime-specific fix rounds, cancellation, or recovery. These references supply the runtime
mechanisms; the shared contract below still governs both paths. Stop if the runtime cannot
perform a required operation rather than substitute an unqualified mechanism silently.

## Workflow and execution mode

The **HITL workflow** returns to the human after each bounded execution. The **handoff workflow**
chains bounded executions through `iterate-design` within the human's approved contract.
Either workflow can use either **execution mode**: **sequential execution**, one writer at a time
(the lead or one delegated writer), or **parallel execution**, two or more writing workers at once.
Read-only workers do not change the execution mode. Neither setting is stored on a work item.

Choose parallel execution when at least two items in the fixed set are ready and separable, their
mutable outputs and resources can be isolated or exclusively scheduled, and actual worktree
isolation and distinct Beads actors are available. Overlapping files are allowed when behavioral
responsibilities are separable in separate worktrees; an unsettled shared interface is a
prerequisite to settle before dispatch. Otherwise choose sequential execution. State the mode,
behavioral ownership, known file overlap, and resource allocation before dispatch; the human may
override.

Both workflows run on a dedicated branch and land through a review surface: a PR, or the branch
diff where the project hosts no PRs. At the first HITL bounded execution, propose the branch;
one branch may span several bounded executions. Parallel workers integrate into that branch,
never into `main`. Ask before pushing or opening a PR in the HITL workflow. Merge stays
human-owned. Local HITL landing requires explicit human instruction, recorded by the lead;
it is never the default.

## Agent team

An agent team is the lead and the workers it dispatches for this execution. When the lead is the
sole writer, it is also the assignee: a team of one. One delegated writer is sequential execution too.

| Agent | Writes | Concurrency | Checkout |
| --- | --- | --- | --- |
| Lead | Execution record, work graph, design doc, integration | One per execution | The target checkout |
| Writing worker | Its own claim, evidence comments, and its item's files | At most the announced finite writing-worker cap | Its own worktree whenever another agent can write at the same time; a sole writer may share the lead's checkout |
| Read-only worker (explorer, reviewer, verifier) | Nothing; returns evidence and findings to the lead | Within actual runtime capacity and limits; at most one verifier | No worktree needed |

- While delegated workers run, the lead is the only agent that edits the active design doc, changes
  the work graph, or writes an item's `dotbrain_` metadata. A writing worker writes only its own claim and,
  when assigned, evidence comments on its own item. It returns candidate results, check evidence,
  discovered work, and design-relevant learning; the lead records them.
- A work item has at most one active worker. When parts of one item could run concurrently, ask the
  human before the execution starts; on agreement split the item through `manage-work-graph`, and
  both parts join the fixed item set.
- A writing worker's own checkpoint checks run in its checkout as part of its work and are not
  verifier runs. It stops after 3 consecutive failed checks on one checkpoint unless the request
  names another limit.
- Send a read-only worker only when the verification economy and delegation boundary say it is
  worth its cost.

## Stop before you start

- No authorized scope: the request names no item, batch, or epic. Ask.
- A `learn:` bead is not execution work. Leave it out. A human-gated scoped item blocks:
  retain it in scope, leave its dependents waiting, and continue only proven independent items
  under the containment rules below in either workflow.
- The required checks cannot be stated. Ask.
- A required capability is missing — worktree isolation for concurrent writers, a distinct Beads
  actor per worker, or an independent reviewer when review is required. Stop and report; never
  weaken the contract to fit the runtime. If only optional parallelism is missing, report the
  serial fallback before continuing, keeping scope, isolation, checks, and gates.

## Operations

Fix the item set at invocation. The set may include waiting dependents; readiness filters that
set, and an unrelated ready item never expands it. Dispatch only from the actual ready frontier
after prerequisite acceptance and closure, with human gates resolved and capacity available.
Establish required checks, retry limits, the worker cap, and any overall limits before work
starts. For an epic scope, `bd swarm validate <epic>` shows dependency waves and maximum
parallelism and `bd swarm status <epic>` shows progress; never run `bd swarm create`.

The lead holds live assignments, pending joins, and the next operation in its own session.

### Dispatch capacity and isolation

The authorized item count and active writing-worker cap are separate. Unless the human specifies
the cap, select and announce a finite cap from actual runtime capacity, resource isolation, and
stated limits. Account for capacity consumed by the lead and required review and verification
operations, including nested agents. Human gates and explicit budgets and caps remain binding.

Fill available writing slots from eligible ready items inside the fixed scope; refill as workers
finish. A returned candidate frees a writing slot without accepting its item or releasing its
claim. Resume a worker for repair only when a writing slot is available. Reduce concurrency when
integration, checks, or shared resources become bottlenecks; capacity never expands scope or
releases a dependent whose prerequisite is not accepted.

Give simultaneous writers separate worktrees and mutable outputs or resource instances where
possible; schedule genuinely shared resources exclusively. Build outputs, databases, and ports
still constrain parallelism. Actual worktrees, claims, resource ownership, and exclusive
scheduling establish isolation; instructions to avoid collisions do not. Serialize integration
into the target and route needed rebases to the original workers.

| Operation | Required input or gate | Result and next operation |
| --- | --- | --- |
| Select | Authorized scope, ready frontier, human gates, routing hints, and limits. | Fixed item set and eligible members; any split agreed with the human first. |
| Dispatch and claim | Required capabilities, the worker cap, and resource constraints. | A `Dispatched` record and an item claimed under the worker's own actor, or a surfaced blocker. |
| Work | Referenced design and unchanged acceptance criteria. | Candidate artifacts and check evidence. A failed check enters bounded repair. |
| Integrate provisionally | Passing worker checks, coherent group membership, and the accepted delivery head; workers remain assignees. | Create an isolated group candidate branch from the accepted delivery head. For each candidate, rebase the item branch onto the current group candidate, then fast-forward the group candidate with `git merge --ff-only <item-branch>`; never create a merge commit. On conflict, resume the original worker and rerun checks. Keep all members open and dependents held. |
| Integration review | Exact integrated revision, group base, included items, and acceptance criteria. | Required independent review, recorded exemptions, or bounded review-fix rounds; lead records the returned report on members. |
| Check | Exact integrated group revision, combined checks covering every member, and no other verifier running. The lead runs checks unless the caller names a verifier; `iterate-design` reserves its verifier for the in-loop gate. | Revision-bound evidence. Failures or gaps hold the group; changed patches or context affecting acceptance require refreshed review and check coverage. |
| Promote and apply closure rules | Combined checks, required independent review, each member's acceptance evidence, and resolved human gates at the exact integrated revision. | Fast-forward the agreed delivery branch with `git merge --ff-only <group-branch>` and confirm its head equals the reviewed and checked revision. Then write `dotbrain_phase: verified` and apply native item closure through `manage-work-graph`. Provisional integration alone is never acceptance. |
| Clean up | A closed item whose worker branch is merged. | The worker's worktree and item branch removed without forcing; anything unmerged stays. |
| Release dependents | Prerequisite acceptance and closure, and a base containing its accepted integrated result. | Eligible dependent members may start while independent siblings continue. |
| Finish | All selected items resolved, or a stop or human gate reached. | Bounded result returned to the caller. Design-level verification and review remain separate. |

- A candidate is not acceptance. A returned patch keeps its item open and its claim held; it
  releases writing capacity only, never dependents.
- For code work, keep the agreed delivery branch at its last accepted revision. Provisional
  integration and repairs stay on isolated group candidate branches; review and checks run against
  the exact candidate head. A sole writer may share the lead's checkout on a group candidate branch;
  concurrent writers still need separate worktrees. Preserve existing unaccepted checkout changes
  as a candidate; if a clean accepted delivery head cannot be established safely, hold integration
  and report the blocker rather than reset or rewrite the delivery branch. For other work, name
  the accepted artifact and its target explicitly.
- If the delivery head advances before promotion, rebase or rebuild the group candidate from the
  latest accepted delivery head, route conflicts to original workers, and refresh review and
  combined checks before promotion. Serialize promotion and confirm the exact accepted head before
  closing members or releasing dependents. Preserve held group branches and worktrees; independent
  groups start from the accepted delivery head and can be promoted without the held changes.
- A dependent starts only from a base that contains its prerequisite's integrated result, after the
  prerequisite closes.
- Name every branch with a short slug only, never a work-item ID: branch names and merge messages
  reach the public repo, and the item's `Dispatched` record and `work` artifact already map the
  item to its branch. The `Integrated` record names both the candidate and its rebased
  revision, since rebasing changes commit hashes.
- Clean up with `git worktree remove <path>` and, from the checkout holding the integration target,
  `git branch -d <item-branch>`; never `--force` or `-D`. Remove an accepted group candidate's
  worktree and merged group branch the same way. Also delete any merged branch the runtime
  created for the worker's worktree. An unmerged branch or dirty worktree stays and is reported.
- Repairs stay inside the item's scope and limits. Discoveries become item facts or new work items
  for a later execution; they never join the current set silently.

## Integration review and acceptance

Passing candidates may be provisionally integrated, then reviewed as a coherent group at an exact
integrated revision. Group boundaries follow features, shared interfaces, and independently
verifiable results, not launch waves or whole epics. A group may contain one item. Review promptly
when accepting a completed prerequisite unlocks dependent work; otherwise group related completed
changes. Provisional integration closes no items and releases no dependents.

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
them. The handoff workflow never asks; it reviews every behavior change.

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

On `CHANGES`, resume the same writing worker to fix its candidate using the applicable runtime
reference. The lead sets `dotbrain_phase` to `working` and
appends `## Dispatched: <worker actor> in <checkout> on <branch> @ <base> (fix round <n>)`.
The resumed worker does not touch its claim. When the lead is the sole writer, it repairs its own
work; a delegated sequential worker is resumed like a parallel worker. If the worker cannot
resume, use the existing replacement rules.
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

Before substantive work, a writing worker:

1. Reads the referenced authority.
2. Confirms that `bd where` names the expected Brainspace store. For tracker access, an unwired
   linked worktree needs no preparation: Beads resolves the shared store through the main
   checkout's Git metadata. Runtime references may still prepare the checkout for other reasons.
3. Runs `git switch -c <item-branch> <base>` in its fresh worktree and confirms `HEAD` is the base.
   Runtimes start worktrees from different commits, so never rely on where the worktree began. A
   replacement worker instead continues on the existing item branch in the stopped worker's
   worktree.
4. Claims its item under its own actor: `bd update <id> --claim --actor <worker-actor> --json --quiet`.

A failed readiness step stops the worker and reaches the lead. Launch alone does not authorize edits.

Launch each delegated writing worker in the background, so the launch returns before the worker
finishes. As soon as the runtime identifies the worker, record `## Dispatched` with its checkout,
branch, and base, with the runtime's agent or session ID in the comment body, before waiting on the
worker. A record written after the worker returns leaves no trace of a running worker if the lead
stops, and a fix round or takeover needs that ID. If a runtime can launch only in the foreground,
record `Dispatched` before launching, naming the branch and base, and add the checkout to the
`work` artifact once the worker reports it.

A writing worker keeps its claim until the item closes, including every review-fix round.
Its return supplies the candidate and evidence; it does not change the assignee. A claimed item
stays out of `bd ready`, and a competing actor's claim is rejected, even after its lease expires.
The lead integrates, checks, and writes `dotbrain_` metadata under its own actor. Beads lets only
the assignee close an item, so the lead closes under the worker's actor and names itself in the
reason, which keeps the worker as assignee:
`bd close <id> --actor <worker-actor> --reason "<reason> (closed by <lead-actor>)" --json --quiet`.
Never pass `--force` to `bd close`, which also overrides gates, and never run `bd reclaim` on a
worker's item.
Move a claim only for a replacement after the previous worker is confirmed stopped:
`bd update <id> --assignee <new-actor> --force`, recording `Claim moved: <from actor> -> <to actor>`.
Beads refuses to reassign a live claim without `--force`; the confirmed stop is what makes forcing
it legitimate. When termination is uncertain, ask the human.

A session the user launches in a worktree attaches with explicit `dotbrain wire` and is the lead of
its own execution.

## Execution record

The lead keeps each item's recoverable facts on the existing bead: native status, assignee, and
dependencies; flat `dotbrain_` metadata keys for current phase, attempts, and artifacts; and headed
append-only evidence comments. The fields, write method, and comment headers are in
[references/execution-record.md](references/execution-record.md). No execution-only or batch-anchor
beads.

## Failure, cancellation, and recovery

An item blocks after 3 consecutive failed checks on one checkpoint, 3 consecutive item-review
`CHANGES`, or a human gate. In both workflows, hold a failed or incompletely covered integration
group and its dependents. Report accepted, failed, blocked, and uncovered work explicitly.
Report every blocked item with its attempt trail and a recommended decision, including waiting
dependents. Keep blocked items in the fixed scope; do not drop them to claim success. Missing
results never count as passes. The conditions that end the whole handoff, and when a PR may be
marked ready, belong to `iterate-design`.

Continue unrelated authorized work only with evidence of accepted bases and isolated integration
candidates. A held contribution on a group candidate cannot silently become another item's base.
Before continuing, record the accepted revision, affected files/resources and consumers, ownership,
and containment checks. Preserve failed candidates and worktrees; use accepted bases and isolated
integration candidates while retaining the held contribution and unrelated accepted work.
Reconsidering a failed group as smaller groups requires a new explicit review boundary and fresh
combined acceptance evidence; prior individual verdicts alone are insufficient.
Serialize shared repair with an explicit file/resource boundary and recorded before/after revisions
and checks. Stop affected writers while that resource is exclusively held. If containment cannot
be proven, stop dispatch and integration; shared-state compromise or unresolved scope, safety, or
acceptance decisions stop the entire execution. Cancellation remains a whole-execution stop.

- **Retry exhaustion.** The affected worker stops and returns attempts, evidence, and remaining
  uncertainty. The lead records a `Blocked` comment, adds the `human` label, keeps the item open,
  and records a concrete decision needed with a recommendation. In either workflow, continue only
  proven independent items under the containment rules above; blocked groups and their dependents
  wait. Preserve candidates, worktrees, claims, original workers, budgets, attempt counts, and
  review history. Resume original workers within remaining limits; replacements require confirmed
  termination and retain those limits. Only the human authorizes more attempts or
  changed criteria; record the decision and new limit, keeping the attempt history.
- **Cancellation.** Stop new dispatch and integration and ask workers to stop. Preserve unfinished
  changes and worktrees, record available progress with a `Cancelled` comment, and leave items
  open. Report any worker whose termination is uncertain before releasing its claim. Cancellation
  authorizes no cleanup, reversal, or design abandonment.
- **Resume.** Only a user-requested resume establishes a replacement lead. Reconcile active
  workers, claims, records, artifacts, and the target revision first. Keep scope, attempt counts,
  checks, limits, and pending human gates; worker replacement and resume never reset a failure
  streak. A replacement worker continues in the stopped worker's worktree named by the item's
  `work` artifact, and the claim moves with a `Claim moved` comment. When ownership or limits
  cannot be established, surface that instead of continuing. Reconstruct item-level next steps;
  do not promise to restore the former batch exactly or pick a different one.

## Completion

Every item in the fixed set is closed with integrated acceptance evidence, or is open with a
recorded blocker, human gate, or cancellation. Workers' merged worktrees and branches are removed.
Return to the caller the closed items, open items with their state, discovered work, and
design-relevant learning for the lead to record.
