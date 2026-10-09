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
Unless you specify a cap, the lead announces a finite active-writing cap based on runtime capacity,
resource isolation, and limits. It reserves capacity for lead, review, and verification operations.
The authorized issue count is separate from this cap.
:::

### Stay involved after each execution

`run-execution` handles that bounded work. The lead proposes a dedicated branch at the first
execution, checks the result, and returns to you. The same branch can hold later executions.
It asks before pushing or opening a PR; merging stays with you.

The lead shows the issues, behavioral ownership, known file overlap, and integration branch before dispatch, and you can
change the split. It keeps the batch inside the agreed scope.

### Hand off an active design

`iterate-design` requires explicit invocation. The design must be active and have
mechanical checks and a hard stop. Before implementation, the lead proposes scope, branch and
base, checks and review, worker cap, human gates, and PR delivery. It also confirms the provider,
authentication, a distinct agent identity, and the required branch ruleset.

Your `GO` authorizes the agreed implementation and delivery: push the dedicated branch, open a
draft PR at the first push, push each accepted integration group, then mark the PR ready and
request your review after successful verification and review. It does not authorize merge,
deployment, publication, dependency changes, or changes to scope or success criteria.

## When Work Can Run in Parallel

For orders pagination, a query implementation and an update to a client SDK might be separate
issues. They can run together only if the API contract is already settled, neither depends on the
other's unfinished code, and mutable resources are isolated or scheduled exclusively. Separable
changes may touch the same files in separate worktrees. If both need to
change the response schema, settle that prerequisite first.

Before dispatching, the lead checks that:

- At least two scoped issues are ready together, with no open blockers.
- Each worker has explicit behavioral ownership and known file overlap; shared interfaces are settled.
- Mutable build outputs, databases, and ports are isolated or scheduled exclusively.
- Each worker can have its own worktree and a distinct Beads actor for claims and evidence.

Separate worktrees isolate edits; they do not isolate database access or filesystem permissions.
When safe parallel work is unavailable, the lead explains why and proceeds one issue at a time
if parallelism was optional. A missing required capability stops the work.

The fixed scope may include waiting dependents. They become eligible only after prerequisite
acceptance and closure, resolved human gates, and a ready-frontier check; capacity never adds
unrelated issues. The lead fills and refills available slots from ready issues inside the fixed scope, reducing
concurrency when integration, checks, or shared resources become the bottleneck. A candidate return
frees writing capacity; it does not accept the issue or release its claim.

Both workflows use a dedicated delivery branch kept at its last accepted revision. Integration
is serialized on isolated group candidate branches from that revision. Passing candidates may be
provisionally integrated before review; their issues remain open and release no dependents.
Changes never go directly into `main`. Where a project has no PR host, the branch diff
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
A review assignment identifies the reviewer, review number, exact base/head, included issues,
and their acceptance criteria.

### How the coding agent runs them

Claude Code receives the roles from the plugin. `run-execution` dispatches packaged roles by name,
with `dotbrain:worker` in the background and worktree isolation for concurrent changes.
Packaged jobs start with their own assignment rather than a fork of the lead's conversation.

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

### Keep assignments focused

The lead supplies the constraints and exact authority sections each job needs, rather than copying
the whole conversation. Where Codex exposes a history control, bounded jobs start without inherited
conversation history; if the runtime cannot bound history, the lead reports that limitation.
Assignments retain project rules, acceptance criteria, ownership, permissions, required skills,
and task-specific overrides. They omit duplicated role defaults and the lead's Beads actor,
while keeping the worker's own actor.
Agents inherit the configured model unless you explicitly request a different model;
packaged roles retain their effort settings without pinning a model. Separate Codex CLI writing
sessions explicitly set medium effort on launch and resume, since reading a worker definition
does not apply its TOML settings. A user-requested model is applied again on resume.

For CLI workers, the lead checks process exit, session and turn outcomes, error events,
nested-process termination, and artifacts, then reads the final response. It reads transcript
prose and tool output when those signals reveal a failure that needs diagnosis.

Workers return the candidate revision and branch, one line per check, and discoveries, blockers,
or design impact when present. Failed checks retain failing test names and error text; the lead
checks claim state directly in Beads. Reviewers return complete structured reports and write no
work-graph comments. Reports name base/head, included issues, acceptance coverage, per-issue
verdicts, stable finding IDs, affected issues, severity, location, problem, and material limits.
The lead preserves reviewer identity, revisions, wording, severity, and verdicts in member records
before routing repairs. A cross-issue finding has one responsible worker and a full durable record
on its issue; other affected issues reference that comment and finding ID. Ownership notes are
the lead's additions; disagreements go back to the reviewer or you. Direct reviews return findings; approval without findings
returns `APPROVE`, with a brief evidence or scope caveat only when material.
Simplification reviews retain their findings-only format.

When no gate command ran, the verifier returns `not run`, why, and what is needed, with available
revision and environment information. It omits an empty record table and PR-ready block.
Partial or failed runs preserve observed results and verbatim failure evidence. Completed gates
keep the full record and public Verification block, with passing logs summarized.

## From Assignment to Accepted Result

1. **Prepare.** The lead fixes the issue set, branch, checks, and ownership. Each delegated worker
   claims its issue under its own Beads actor and keeps that claim through review fixes.
2. **Implement.** The worker makes its change, runs the checkpoint checks, commits the candidate,
   and returns its revision, results, discoveries, and blockers.
3. **Provisionally integrate.** The lead serializes integration of passing candidates into an
   isolated group candidate branch from the accepted delivery head. Issues stay open with their
   claims, and dependents wait; the delivery branch stays at its accepted head.
4. **Review and check.** An independent reviewer covers a coherent group at the exact integrated
   revision, including unchanged consumers and interactions. Combined checks cover every member's
   acceptance criteria. Review promptly when accepting a prerequisite can unlock dependent work;
   groups follow completed features and interfaces, not whole launch waves or epics.
5. **Accept and record.** Once acceptance and human gates are satisfied, the lead fast-forwards
   the delivery branch to the exact reviewed and checked candidate head, records evidence,
   and applies the closure rules. If the delivery head advanced, first rebase or rebuild the
   candidate from that accepted head and refresh review and combined checks. For a delegated issue
   it closes under the assignee's actor,
   naming the lead in the reason; the worker does not close the issue or hand back its claim.

### Review-fix loop

The lead sends the integrated group to an independent reviewer. An unmet acceptance criterion or
a change-caused blocker/high regression produces `CHANGES`, even in an unchanged consumer.
Unrelated existing defects are discovered work; medium/low findings remain non-blocking. Safety
claims need evidence, a concrete trace, or a small targeted check; missing evidence is a gap.
If the reviewer returns `CHANGES`, the lead records the report before sending the durable finding
references back to the original responsible worker, which fixes the change in the same checkout,
reruns its checks, and commits the fix. The lead then asks the same reviewer to review it again.
The same reviewer checks the fixes and affected interactions. Passing worker checks alone do not
resolve findings. Three consecutive `CHANGES` verdicts hold the affected group for your decision.
Group records retain revision ranges, member coverage, review provenance, checks, and finding
references. Changed patches or integration context affecting coverage need refreshed evidence.
Closure and dependent release wait for required review, combined checks, acceptance, and human
gates; dependents start from a base containing accepted prerequisites.

The worker's own tests are checkpoint evidence, not independent acceptance. The lead normally
runs integrated item checks itself; a handoff reserves the `verifier` for the final in-loop gate.
Only one verifier runs at a time.

Code, tests, build/CI configuration, and agent instructions require independent review;
prose-only changes are exempt. In HITL, the lead can ask you to exempt a small change and states
its recommendation. A multi-item branch requires independent whole-branch code review before
delivery. The final integration review can supply it only with explicit coverage of the entire
branch diff, all scoped items, interactions, and the active design at the exact final revision.
Approval of only the latest group is insufficient. The reviewer must have authored none of the
reviewed changes, but need not be fresh. Otherwise arrange a whole-branch review. Mechanical
checks, the final human review record, and your merge gate remain.
A single-item branch reuses its item review only if it covers the whole final diff; otherwise it
also needs a whole-branch review.
A handoff also gets a non-blocking simplification pass when an independent reviewer is available;
you decide what to do with its suggestions.

## When Something Stops

An issue stops after three consecutive failed checks on one checkpoint, three consecutive
`CHANGES` item-review verdicts, or a human gate. The lead preserves the attempt trail and explains
the decision needed. Only you authorize more attempts or changed criteria.

In either workflow, a failed integration group and its dependents wait while genuinely independent
scoped issues continue. The lead preserves the held revision, findings, claims, and attempt counts,
and proves isolation from the failed group. Independent work starts from accepted bases and uses
isolated integration candidates; failed contributions and unrelated accepted changes are preserved.
Held group branches stay separate from the delivery branch, so another accepted group can be
promoted without the held changes. Recovery never resets or rewrites the delivery branch.
If isolation cannot be established, report the blocker and stop affected work. Splitting a failed
group requires explicit new review boundaries and fresh evidence; earlier item verdicts alone do
not accept the changed group. The handoff
ends blocked when no unblocked work remains; its PR stays draft while any scoped issue is blocked.

A whole handoff stops immediately for a missing required capability, compromised shared state,
an action outside the approved contract, unresolved scope or safety questions, or criteria that
cannot be met. It also stops after two cycles without progress, or when you cancel it.

Cancellation preserves unfinished files, branches, worktrees, and evidence. A replacement takes
over a claim only after the previous worker is confirmed stopped; a returned result or expired
lease does not prove that. Recovery keeps the original scope, checks, and attempt history.

## Investigate Before Asking

For an unknown, inspect observable facts first and research recorded history when rationale
matters; current code alone does not establish historical intent. Report evidence, inference,
unresolved gaps, the cheapest next action, and whether it blocks the decision, or defer it with a
reason. Small experiments stay within existing scope and limits. Reversible implementation
defaults can be chosen within scope; preferences, authority, acceptance changes, consequential
tradeoffs, and evidence-unsettled decisions come to you with evidence and a recommendation.
`find-unknowns` stays read-only. Active designs own initiative uncertainty, Beads owns execution
state, and established workflows own durable canon. Designs and issue decomposition use concrete
seams, independently verifiable outcomes, verification boundaries, and interface/resource dependencies.

## Related

- [Example prompts](prompts.md#work) provides requests for each workflow and mode.
- [The workflow](workflow.md) follows a feature from planning to a closed design.
- [Session context](session-context.md#subagents) explains how packaged roles reach the runtime.
- [Skills](skills.md) lists the procedures that coordinate the work.
