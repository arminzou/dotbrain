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

Choose parallel execution when at least two items in the fixed set are ready, their predicted file
ownership does not overlap, no shared resource collides, and worktree isolation and distinct Beads
actors are available. Otherwise choose sequential execution. Write ownership into each assignment
and respect the worker cap. In the HITL workflow, state the mode and ownership split before
dispatch; the human may override.

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
| Writing worker | Its own claim, evidence comments, and its item's files | At most the cap at once, 2 by default | Its own worktree whenever another agent can write at the same time; a sole writer may share the lead's checkout |
| Read-only worker (explorer, reviewer, verifier) | Its own item-review comment when assigned as reviewer; otherwise nothing | Uncapped, except at most one verifier | No worktree needed |

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
  in the HITL workflow stop for sign-off; in the handoff workflow retain it in scope as blocked,
  leave its dependents waiting, and continue independent items.
- The required checks cannot be stated. Ask.
- A required capability is missing — worktree isolation for concurrent writers, a distinct Beads
  actor per worker, or an independent reviewer when review is required. Stop and report; never
  weaken the contract to fit the runtime. If only optional parallelism is missing, report the
  serial fallback before continuing, keeping scope, isolation, checks, and gates.

## Operations

Fix the item set at invocation. Readiness filters that set; an unrelated ready item never expands
it. Establish required checks, retry limits, the worker cap, and any overall limits before work
starts. For an epic scope, `bd swarm validate <epic>` shows dependency waves and maximum
parallelism and `bd swarm status <epic>` shows progress; never run `bd swarm create`.

The lead holds live assignments, pending joins, and the next operation in its own session.

| Operation | Required input or gate | Result and next operation |
| --- | --- | --- |
| Select | Authorized scope, ready frontier, human gates, routing hints, and limits. | Fixed item set and eligible members; any split agreed with the human first. |
| Dispatch and claim | Required capabilities, the worker cap, and resource constraints. | A `Dispatched` record and an item claimed under the worker's own actor, or a surfaced blocker. |
| Work | Referenced design and unchanged acceptance criteria. | Candidate artifacts and check evidence. A failed check enters bounded repair. |
| Item review | Passing worker checks and the candidate diff against its base. | Independent item review, a recorded exemption, or bounded review-fix rounds. |
| Integrate | Reviewed candidate and intended target; the worker remains assignee. | Integrated result. On a conflict, resume the worker to rebase onto the current target and rerun checks. Keep the item open. |
| Check | Integrated result, agreed item checks, and no other verifier running. The lead runs item checks itself unless the caller names a verifier; `iterate-design` reserves its verifier for the in-loop gate. | Revision-bound evidence. A failure returns to the worker as a repair; review any new behavior diff before closure. |
| Apply closure rules | Passing acceptance evidence, resolved item-level human gates, and review of every behavior diff since the last approval. | `dotbrain_phase: verified` written, then native item closure through `manage-work-graph`. |
| Clean up | A closed item whose worker branch is merged. | The worker's worktree and item branch removed without forcing; anything unmerged stays. |
| Release dependents | Prerequisite closure and a base containing its integrated result. | Eligible dependent members may start while independent siblings continue. |
| Finish | All selected items resolved, or a stop or human gate reached. | Bounded result returned to the caller. Design-level verification and review remain separate. |

- A candidate is not acceptance. A returned patch keeps its item open and releases nothing.
- For code work, integration targets the agreed branch and checks run against the actual integrated
  revision. Work done in the target checkout under the HITL workflow may already be integrated, but still
  needs acceptance evidence. For other work, name the accepted artifact and its target explicitly.
- A dependent starts only from a base that contains its prerequisite's integrated result, after the
  prerequisite closes.
- Clean up with `git worktree remove <path>` and, from the checkout holding the integration target,
  `git branch -d <item-branch>`; never `--force` or `-D`. Also delete any merged branch the runtime
  created for the worker's worktree. An unmerged branch or dirty worktree stays and is reported.
- Repairs stay inside the item's scope and limits. Discoveries become item facts or new work items
  for a later execution; they never join the current set silently.

## Item review

Every work item's behavior change gets an independent `code` item review before integration in
parallel execution, and before closure in sequential execution. Behavior includes code, tests,
build or CI config, and instructions agents execute: skills, prompts, and agent definitions.
Changes confined to human-facing prose docs, comments, formatting, or generated output are exempt;
the lead records `## Review skipped: <reason>` on the work item.

In the HITL workflow only, the lead may ask whether a small behavior change needs review. The
prompt includes the diffstat, the behavior changed, and the lead's recommendation. Keep the item
open until the human answers. Record a decline as
`## Review skipped: declined by human — <reason>`. Standing answers hold until the human changes
them. The handoff workflow never asks; it reviews every behavior change.

Use a reviewer agent that authored none of the reviewed change. The lead never reviews changes
it authored. Fix the boundary at the item's diff against its base and its acceptance criteria.
The reviewer appends `## Review <n>: APPROVE | CHANGES @ <revision>` to the work item under its own
Beads actor, naming that actor and each finding's severity (`blocker`, `high`, `medium`, `low`)
and `file:line`. An item review never gets a review bead.

Return `CHANGES` only for an unmet acceptance criterion or a `blocker` or `high` finding in the
item's own diff. Return `APPROVE` with `medium` or `low` findings and findings outside the diff;
the lead files those as discovered work for a later bounded execution.

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

Parallel order: work and passing worker checks, candidate, item review and fix loop, integrate,
integrated check, close as `verified`, clean up, release dependents. Sequential order: work,
checks, item review and fix loop, close. A conflict rebase does not count toward the `CHANGES` cap.
Any behavior diff after the last `APPROVE`, including a conflict rebase or integrated-check repair,
gets an item review of that diff before closure. No item closes with an unreviewed behavior change.

## Worker assignment

Every delegated worker receives a compact assignment in its runtime message:

- work-item IDs and the assigned operation
- the worker's Beads actor, passed as `--actor <worker-actor>` on every `bd` write; without it the
  actor is the shared Git user, and a repeated claim by the same actor succeeds silently
- the lead's Beads actor, for integration, metadata writes, and closure
- allowed actions and file or resource ownership
- checkout, item branch, and base revision, where applicable
- the commit convention to follow: the repository's written commit rules, or else the style of
  its recent history
- absolute paths to the controlling design, the Brain's `AGENTS.md`, the acceptance criteria, and
  required checks
- retry limit, escalation rules, and the artifacts, evidence, and blockers to return

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
stays out of `bd ready`, and a competing actor's claim is rejected. The lead integrates, checks,
writes `dotbrain_` metadata, and closes under its own actor while the worker remains assignee.
Move a claim only for a replacement after the previous worker is confirmed stopped, recording
`Claim moved: <from actor> -> <to actor>`. When termination is uncertain, ask the human.
Beads itself lets any actor reassign, so this rule is the guard.

Build outputs, databases, and ports still constrain parallelism; separate worktrees do not prove
those are independent.

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
`CHANGES`, or a human gate. In the handoff workflow, only that item and its dependents stop;
independent items continue, and an item block alone never ends the handoff. Report every blocked
item with its attempt trail and a recommended decision, including waiting dependents. Keep
blocked items in the fixed scope; do not drop them to claim success. The HITL workflow instead
pauses new dispatch and integration and asks the human. The conditions that end the whole
handoff, and when a PR may be marked ready, belong to `iterate-design`.

- **Retry exhaustion.** The affected worker stops and returns attempts, evidence, and remaining
  uncertainty. The lead records a `Blocked` comment, adds the `human` label, keeps the item open,
  and records a concrete decision needed with a recommendation. In the handoff workflow, continue
  independent items within the fixed scope; blocked items and their dependents wait. In the HITL
  workflow, ask the human and pause new dispatch and integration across the execution. Running
  unaffected workers may reach a safe checkpoint within their limits and return candidates; a
  compromised shared resource or target stops them. Only the human authorizes more attempts or
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
