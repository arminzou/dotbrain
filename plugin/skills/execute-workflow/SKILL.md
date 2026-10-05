---
name: execute-workflow
description: Carries out one work item or a finite batch from the private work graph — selects, dispatches workers, integrates, checks, repairs within limits, closes through manage-work-graph, and escalates or recovers. Use when asked to do, implement, or work an item, a set of items, or an epic's ready work, or via /dotbrain:execute-workflow. NOT for filing or reshaping work items (manage-work-graph), a design-level automation handoff (iterate-design), or independent review (review-gate).
---

# Execute Workflow

Run one bounded execution: one work item by default, or an explicit finite batch of item IDs. The
work graph says what depends on what; this skill owns the **execution graph** — how an agent team
carries out the fixed item set — and each item's **execution record**. Graph maintenance and
closure rules stay with [`manage-work-graph`](../manage-work-graph/SKILL.md).

A plain action request ("do X", "work the ready items under this epic") starts this skill.
Calling it does not require spawning another agent.

## Agent team

An agent team is the lead and the workers it dispatches for this execution. Sequential execution is
a team of one: the lead is also the assignee and the only worker.

| Agent | Writes | Concurrency | Checkout |
| --- | --- | --- | --- |
| Lead | Execution record, work graph, design doc, integration | One per execution | The target checkout |
| Writing worker | Its own claim, evidence comments, and its item's files | At most the cap at once, 2 by default | Its own worktree whenever another agent can write at the same time; a sole writer may share the lead's checkout |
| Read-only worker (investigator, reviewer, verifier) | Nothing; it reports back | Uncapped, except at most one verifier | No worktree needed |

- While delegated workers run, the lead is the only agent that edits the active design doc, changes
  the work graph, or writes an item's `dotbrain` object. A worker writes only its own claim and,
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
- An item in the set is human-gated or a `learn:` bead. Leave it out or stop for sign-off.
- Required checks, the retry limit, or the writing-worker cap cannot be stated. Ask.
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
| Integrate | Candidate revision or artifact, intended target, and the claim handed back. | Integrated result. Keep the item open. |
| Check | Integrated result, agreed item checks, and no other verifier running. The lead runs item checks itself unless the caller names a verifier; `iterate-design` reserves its verifier for the in-loop gate. | Revision-bound evidence, or bounded repair within the same item. |
| Apply closure rules | Passing acceptance evidence and resolved item-level human gates. | Native item closure through `manage-work-graph`. |
| Clean up | A closed item whose worker branch is merged. | The worker's worktree and item branch removed without forcing; anything unmerged stays. |
| Release dependents | Prerequisite closure and a base containing its integrated result. | Eligible dependent members may start while independent siblings continue. |
| Finish | All selected items resolved, or a stop or human gate reached. | Bounded result returned to the caller. Design-level verification and review remain separate. |

- A candidate is not acceptance. A returned patch keeps its item open and releases nothing.
- For code work, integration targets the agreed branch and checks run against the actual integrated
  revision. Work done interactively in the target checkout may already be integrated, but still
  needs acceptance evidence. For other work, name the accepted artifact and its target explicitly.
- A dependent starts only from a base that contains its prerequisite's integrated result, after the
  prerequisite closes.
- Clean up with `git worktree remove <path>` and, from the checkout holding the integration target,
  `git branch -d <item-branch>`; never `--force` or `-D`. Also delete any merged branch the runtime
  created for the worker's worktree. An unmerged branch or dirty worktree stays and is reported.
- Repairs stay inside the item's scope and limits. Discoveries become item facts or new work items
  for a later execution; they never join the current set silently.

## Worker assignment

Every delegated worker receives a compact assignment in its runtime message:

- work-item IDs and the assigned operation
- the worker's Beads actor, set through `BEADS_ACTOR` (the default actor is the shared Git user, and
  a repeated claim by the same actor succeeds silently)
- allowed actions and file or resource ownership
- checkout, item branch, and base revision, where applicable
- absolute paths to the controlling design, the Brain's `AGENTS.md`, the acceptance criteria, and
  required checks
- retry limit, escalation rules, and the artifacts, evidence, and blockers to return

Before substantive work, a writing worker:

1. Reads the referenced authority.
2. Confirms that `bd where` names the expected Brainspace store. An unwired linked worktree needs
   no preparation: Beads resolves the shared store through the main checkout's Git metadata.
3. Runs `git switch -c <item-branch> <base>` in its fresh worktree and confirms `HEAD` is the base.
   Runtimes start worktrees from different commits, so never rely on where the worktree began. A
   replacement worker instead continues on the existing item branch in the stopped worker's
   worktree.
4. Claims its item under its own actor: `bd update <id> --claim --json --quiet`.

A failed readiness step stops the worker and reaches the lead. Launch alone does not authorize edits.

On return, the worker's last step hands its claim back: `bd assign <id> <lead-actor>` and a
`Claim moved: <worker> -> <lead>` comment. The lead is the assignee while it integrates, checks, and
closes. The lead reclaims from a worker only once that worker is confirmed stopped; when the runtime
cannot tell, ask the human. Beads itself lets any actor reassign, so this rule is the guard.

In Claude Code, dispatch each concurrent writing worker as a subagent with worktree isolation on the
call, using a role allowed to create a branch and commit, such as the general-purpose agent. The
packaged `implementer` cannot: it is a sole writer sharing the lead's checkout for a small change,
and it refuses an item that needs a branch. The isolation guard refuses git commands it cannot
attribute to the worker's worktree, including chained commands and commands a shell hook rewrites;
tell workers to run git as plain, separate commands and to set commit identity through the
`GIT_AUTHOR_*` and `GIT_COMMITTER_*` environment variables. Build outputs, databases, and ports still constrain
parallelism; separate worktrees do not prove those are independent.

A session the user launches in a worktree attaches with explicit `dotbrain wire` and is the lead of
its own execution.

## Execution record

The lead keeps each item's recoverable facts on the existing bead: native status, assignee, and
dependencies; a `dotbrain` metadata object for current phase, attempts, and artifacts; and headed
append-only evidence comments. The fields, write method, and comment headers are in
[references/execution-record.md](references/execution-record.md). No execution-only or batch-anchor
beads.

## Failure, cancellation, and recovery

- **Retry exhaustion.** The affected worker stops and returns attempts, evidence, and remaining
  uncertainty. The lead records a `Blocked` comment and `phase: awaiting_human`, adds the `human`
  label, keeps the item open, and asks the human for a concrete decision with a recommendation.
  While that decision is pending, pause new dispatch and integration across the execution. Running
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
