# Working with an Agent Team

Your coding agent can do a change itself or assign focused work to other agents. An **agent team**
is the lead and the workers it dispatches for one bounded execution: one issue or a fixed batch
with agreed checks. You stay in the main conversation while the lead prepares assignments,
collects results, and brings decisions back to you.

This guide uses pagination for `GET /orders` as an example. The design and issues are already
settled; see [The workflow](workflow.md) for the steps that get you there.

## Who Does What

| Role | Responsibility |
|---|---|
| You | Approve acceptance and success criteria, resolve human gates, authorize delivery, and decide whether to merge. |
| Lead | Your main agent session. Selects the scoped issues, assigns work, arranges review, integrates results, checks them, and maintains the execution record. |
| Assignee | The agent holding an issue's claim in Beads. Ownership stays with it through implementation and review fixes. |
| Worker | An agent carrying out an assignment. It may change code or do read-only research, review, or verification. |

The lead can also be the assignee and do the change itself: a team of one. Delegating one change
to one worker still means only one agent changes code at a time.

While delegated workers run, the lead alone maintains the work graph and active design. Workers
return discoveries to it instead of changing the plan themselves. A result coming back is a
candidate; the lead still needs review and verification evidence before accepting it.

## Two Independent Choices

Choose the **workflow** according to how you want to stay involved, and the **execution mode**
according to which tasks can safely run together.

| Workflow | Sequential execution | Parallel execution |
|---|---|---|
| **HITL** (Human-in-the-Loop) | The agent completes a bounded execution and returns to you. One agent changes code at a time. | The lead assigns independent issues to workers and returns the batch results to you. |
| **Handoff** | The agent continues through the approved design, one issue at a time. | The agent continues through the design, running independent issues together where safe. |

Read-only research, review, and verification do not change the execution mode. A worker fixing
one issue while a reviewer reads another is still sequential execution.

::: info Defaults
HITL with sequential execution is the default; you do not need to name either in your prompt.
Parallel execution defaults to up to two workers changing code at once, in either workflow.
Specify a different cap only when you want to change it.
:::

### Stay involved after each execution

`run-execution` handles that bounded work. The lead proposes a dedicated branch at the first
execution, checks the result, and returns to you. The same branch can hold later executions.
It asks before pushing or opening a PR; merging stays with you.

The lead shows the issues, file ownership, and integration branch before dispatch, and you can
change the split. It keeps the batch inside the agreed scope.

### Hand off an active design

`iterate-design` requires explicit invocation. The design must be active and have
mechanical checks and a hard stop. Before implementation, the lead proposes scope, branch and
base, checks and review, worker cap, human gates, and PR delivery. It also confirms the provider,
authentication, a distinct agent identity, and the required branch ruleset.

Your `GO` authorizes the agreed implementation and delivery: push the dedicated branch, open a
draft PR at the first push, push each integrated and checked issue, then mark the PR ready and
request your review after successful verification and review. It does not authorize merge,
deployment, publication, dependency changes, or changes to scope or success criteria.

## When Work Can Run in Parallel

For orders pagination, a query implementation and an update to a client SDK might be separate
issues. They can run together only if the API contract is already settled, neither depends on the
other's unfinished code, and their files and shared resources do not overlap. If both need to
change the response schema, settle that prerequisite first.

Before dispatching, the lead checks that:

- At least two scoped issues are ready together, with no open blockers.
- Each worker has explicit file ownership; those assignments do not overlap.
- Build outputs, databases, and ports will not collide.
- Each worker can have its own worktree and a distinct Beads actor for claims and evidence.

Separate worktrees isolate edits; they do not isolate database access or filesystem permissions.
When safe parallel work is unavailable, the lead explains why and proceeds one issue at a time
if parallelism was optional. A missing required capability stops the work.

Both workflows use a dedicated integration branch. Workers' changes reach that branch after
review and checks, never directly into `main`. Where a project has no PR host, the branch diff
provides the review surface. Direct local landing needs your explicit instruction.

## The Packaged Subagents

The plugin supplies four focused roles. A **skill** describes a procedure; a **subagent** carries
out an assignment. In the pagination example, they contribute at different stages:

| Role | Contribution to the team |
|---|---|
| `researcher` | Before implementation, compares pagination approaches against project context and outside evidence. Returns findings for the lead to use in decisions. |
| `worker` | Implements the assigned query or SDK change and commits the candidate. Returns it to the lead for review and integration; never pushes, merges, or closes issues. |
| `reviewer` | Independently checks the candidate for pagination bugs, authorization gaps, compatibility, and missing tests. Required fixes go back to the original worker. |
| `verifier` | Runs the agreed gate against the integrated branch. Returns revision-bound results; failures go back to the lead, not into an automatic fix by the verifier. |

For exploration, the workflows use the coding agent's built-in explorer where available; it is
not another packaged dotbrain role. Delegation is optional when the main agent can do the job
more directly.

The lead prepares complete assignments: checkout and branch, file ownership,
issue and actor where needed, acceptance criteria, checks, and what evidence to return. A worker
will stop on the default branch unless your explicit local-landing instruction was recorded.
An item-review assignment also names the reviewer actor, review number, candidate revision, and diff base.

### How the coding agent runs them

Claude Code receives the roles from the plugin. `run-execution` dispatches `dotbrain:worker`
in the background and uses worktree isolation for concurrent changes.

Codex receives generated agent definitions in each wired checkout. For isolated implementation,
the current workflow creates and wires worktrees, then launches separate Codex CLI sessions with
assignments pointing to the packaged worker definition. A CLI session cannot directly select a
custom agent. Native Codex subagents can take focused assignments, but assigning
one a directory does not establish worktree isolation.

The coding agent runtime owns launching, waiting, and resuming agents. Dotbrain supplies context,
roles, wiring, and workflow rules; Beads holds claims and execution state. Runtime support and
permissions must allow the required operations. See [Session context](session-context.md#subagents)
for delivery and customization.

For role names and ready-to-send requests, see [Example prompts](prompts.md#packaged-subagents).

## From Assignment to Accepted Result

1. **Prepare.** The lead fixes the issue set, branch, checks, and ownership. Each delegated worker
   claims its issue under its own Beads actor and keeps that claim through review fixes.
2. **Implement.** The worker makes its change, runs the checkpoint checks, commits the candidate,
   and returns its revision, results, discoveries, and blockers.
3. **Review.** The lead runs the review-fix loop with an independent reviewer before integration.
4. **Integrate and check.** The lead integrates the reviewed candidate into the dedicated branch
   and runs the agreed checks against the integrated result. New behavior changes need review too.
5. **Accept and record.** Once acceptance and human gates are satisfied, the lead records evidence
   and applies the closure rules. For a delegated issue it closes under the assignee's actor,
   naming the lead in the reason; the worker does not close the issue or hand back its claim.

### Review-fix loop

The lead sends the worker's change to an independent reviewer. If the reviewer returns `CHANGES`,
the lead sends the findings back to the same worker, which fixes the change in the same checkout,
reruns its checks, and commits the fix. The lead then asks the same reviewer to review it again.
The loop ends with `APPROVE`, or stops for your decision after three consecutive `CHANGES` verdicts.

The worker's own tests are checkpoint evidence, not independent acceptance. The lead normally
runs integrated item checks itself; a handoff reserves the `verifier` for the final in-loop gate.
Only one verifier runs at a time.

Code, tests, build/CI configuration, and agent instructions require independent item review;
prose-only changes are exempt. In HITL, the lead can ask you to exempt a small change and states
its recommendation. A multi-item branch gets a fresh whole-branch code review before delivery.
A handoff also gets a non-blocking simplification pass when an independent reviewer is available;
you decide what to do with its suggestions.

## When Something Stops

An issue stops after three consecutive failed checks on one checkpoint, three consecutive
`CHANGES` item-review verdicts, or a human gate. The lead preserves the attempt trail and explains
the decision needed. Only you authorize more attempts or changed criteria.

In **HITL**, the lead pauses new dispatch and integration and comes back to you. In **handoff**,
the blocked issue and its dependents wait while independent scoped issues continue. The handoff
ends blocked when no unblocked work remains; its PR stays draft while any scoped issue is blocked.

A whole handoff stops immediately for a missing required capability, compromised shared state,
an action outside the approved contract, unresolved scope or safety questions, or criteria that
cannot be met. It also stops after two cycles without progress, or when you cancel it.

Cancellation preserves unfinished files, branches, worktrees, and evidence. A replacement takes
over a claim only after the previous worker is confirmed stopped; a returned result or expired
lease does not prove that. Recovery keeps the original scope, checks, and attempt history.

## Related

- [Example prompts](prompts.md#work) provides requests for each workflow and mode.
- [The workflow](workflow.md) follows a feature from planning to a closed design.
- [Session context](session-context.md#subagents) explains how packaged roles reach the runtime.
- [Skills](skills.md) lists the procedures that coordinate the work.
