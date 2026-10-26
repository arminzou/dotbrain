---
name: iterate-design
description: Iterates from an active design doc in Goal mode for an explicit automation handoff with a mechanical verifier and hard stop.
---

# Iterate Design

Use the agent harness's Goal mode when available. Otherwise, keep work in the same task and
make bounded repeated turns.
Do not build or invoke a dotbrain loop runner. dotbrain supplies context, state boundaries, and
reflection rules; the coding agent runs the loop.

## When to use

This loop drives the handoff workflow and is human-triggered: the human explicitly hands a design off to it as an automation handoff, by name
(`/iterate-design`) or in words, and it runs on a dedicated branch — never directly on `main` — even
after a mid-loop return to the human.

Use when:

- Work has an active design doc in `.brain/designs/`.
- The task needs more than one ordinary turn but has a verifiable stopping condition.
- A linked bead or epic exists, or the user explicitly points at a design doc.

Do not use for one-off fixes, pure triage, open-ended brainstorming, or work without a verification
story. Reach for `manage-work-graph`, `find-unknowns`, `grill-decisions`, or `to-design` first.

### Loop-worthiness check

Before starting the loop, confirm all five hold. If any is missing, stay in ordinary turns instead:

1. A mechanical gate exists or can be named (a command, test, build, or metric — not just "looks right").
2. The agent can run what it changes (execute the gate itself, not wait on an external process).
3. The in-loop gate is fast enough to run within the retry budget.
4. A hard stop is set (a retry cap or budget the loop will actually honor).
5. The preflight contract below covers the permitted delivery actions; every other irreversible
   action still has a human gate.

## Preflight contract

Before changing code, locate the human-approved contract in the design or linked handoff record.
Reuse a complete applicable contract without repeat `GO`. Validate scope, branch/base, criteria,
checks/UAT, review expectations, provider/auth and PR authority, and finite limits against the
current environment and instructions. Preserve narrower operator overrides. Ask only for missing
or changed authority, with evidence and a recommendation; stop affected work until resolved.
An execution request does not silently authorize an unapproved contract.

- **Scope:** one named work bead, or every implementation bead under the named design/epic in
  dependency order. Apply manage-work-graph's claim rules.
- **Branch and base:** dedicated branch name, a short slug with no work-item ID, and base branch. Base on
  an unmerged branch only when the work depends on it (a stacked PR targeting that branch's PR);
  work that merely shares a base gets a sibling branch on that base.
- **Verification:** name the checkpoint check and in-loop Success Criteria gate, plus
  the full suite at the review surface. Apply run-execution's role routing and
  review-gate's final review, simplify, and named readiness rules.
- **Workers:** record the writing-worker cap under run-execution's parallel reference.
  Apply its capacity and isolation rules when delegating.
- **Limits:** finite whole-loop budget or turn limit, retry caps, consumed attempts and remaining
  allowance. On resume, retain original workers, claims, worktrees, budgets, per-item attempts,
  review history and hard stops. Resume never resets an exhausted limit or grants new authority.
- **Acceptance/UAT:** agreed user journeys, environment, required evidence and criteria. Record
  revision, environment, what actually ran, outcomes and gaps. Missing evidence is not a pass.
- **Human gates:** every human-gated item in the proposed scope. A handoff that includes one can
  only end `BLOCKED`, so the human sees that before approval. A settled all-autonomous graph is valid.
- **Delivery:** authorize the Handoff delivery sequence below. Confirm the provider and auth, a
  base-branch ruleset requiring a reviewed PR and dismissing stale approvals, and an agent
  identity distinct from the human reviewer; mentions and review requests come from that agent
  identity.

The approved contract authorizes implementation, commits, worktree integration onto the delivery
branch, review/repair, work-record closure under the review rules, agreed acceptance/UAT, pushing
the dedicated branch, opening a
draft PR at the first push, one mention of the human for each blocked stop, and marking the PR
ready with the human's review requested at `FINAL`. It does not authorize PR approval,
target-branch merge, release, deploy, publish,
dependency changes, or changing scope, acceptance, or success criteria. Missing provider/auth,
agent identity, required ruleset, or an unapproved contract is a stop before the loop starts.
At execution entry, check actual provider credentials and permissions without exposing secrets;
availability never implies authorization. Never fall back to the human's credentials.

## Handoff delivery

After the first item passes integration review, combined checks, and acceptance, push the dedicated branch and
open a draft PR at the first push. Record its URL in the private execution record and the active
design, and attach it in the runtime where supported. Do not create a placeholder commit to open
it at preflight. Push after each accepted integration group; hold failed or uncovered contributions.
Push only the accepted delivery branch after candidate promotion; held group branches stay local.
The pushed
commits show progress; post no progress comments and make no body updates between the first push
and FINAL.

When the whole handoff ends BLOCKED, leave the PR draft and post one PR comment that @-mentions
the human with an audience-safe reason. Each blocked stop gets one mention. Check existing
comments and the delivery record before posting or retrying, keyed to this stop's revision and
reason: a retry of the same stop never posts twice, and a new stop after a resume gets its own
mention. Record the comment URL with that key. Keep item IDs, attempt details, and private
context in the tracker and session. Before the first push, use the runtime's own notification
where available, otherwise the session report. A notification failure remains BLOCKED and is
reported in the session.

At FINAL, write the Verification section and the simplify count or skip note, mark the existing
draft PR ready, and request the human's review. Never mark it ready with a blocked scoped item.
Use the project's PR delivery capability for all host actions under the confirmed agent identity.

## Worktree preparation

A dedicated branch may run in place or in a git worktree. When the user launches this session in a
worktree, verify before planning that `.brain` and `.beads` resolve to the main checkout's
Brainspace when enabled. When they are absent, run `dotbrain wire` in the worktree, directly or
through `wire-brain`, before dispatch. The CLI resolves the main checkout through Git metadata and
preserves its registration. For delegated worker checkouts, follow the worker runtime's reference
in `run-execution`; it says whether the checkout needs wiring before launch.

## Read order

Before planning, read:

1. `bd prime` on a new session or after context recovery. dotbrain injects no Beads context; skip
   it only when the operator's own Beads hook already supplied it.
2. Nearest `AGENTS.md`.
3. `.brain/CONTEXT.md`, if present.
4. The active design doc.
5. Linked bead or epic, if present: inspect `bd ready --json --quiet`, `bd human list --json --quiet`,
   and `bd show <id> --json --quiet`. Apply manage-work-graph's claim and actor rules.
6. Relevant `.brain/docs/` references or code files only as needed.

## Controlling instruction document

Treat the active design doc as the loop's controlling instruction document.

It defines objective, scope, non-goals, constraints, the design, known unknowns, success criteria,
and where design-relevant discoveries belong.

If the design doc lacks a `Success Criteria` section, first propose the smallest useful one. If verification is human/product judgment rather than an automated command, state that and
treat it as a human decision gate.

For design/epic scope, repeat run-execution's ready-frontier operation after closure.
Final review records follow review-gate and its review-beads reference.

## Goal-shortfall repairs

Admit a goal-shortfall repair into the running loop. The lead files its fix as a work
item under the epic, records why it is needed to meet the approved
goal, and adds it to the running loop's fixed set. Meeting an approved goal adds no new
scope. The fix shares the existing finite whole-loop budget and limits; admission grants
no extra attempts. Exhausting that budget with the fix open ends `BLOCKED`, never `FINAL`.
A fix needing a new design, scope, authority, or criteria decision still stops affected
work and asks the human under the convention's decision rules. Other discoveries keep
their existing treatment.

## Loop protocol

Use this protocol throughout the handoff:

1. PLAN: Reread the active design doc fresh — do not rely on an earlier iteration's memory of it,
   since long runs are where constraints silently drop out of lossy context. Then select the next
   bounded execution: one ready work item or a fixed finite item set within the approved scope.
   The set may include waiting dependents; dispatch only from the actual ready frontier after
   prerequisite acceptance and closure, with human gates resolved and capacity available. Refill
   eligible slots as prerequisites close while independent siblings continue. Never add items
   silently to an execution already under way.
2. DO: Run that bounded execution through `run-execution`, as its lead. This skill keeps the
   outer loop, reflection, overall limits, final review, and delivery.
3. VERIFY: Apply run-execution's role routing for checkpoint checks. Run the once-only
   in-loop gate before final review.
4. REFLECT: Apply manage-work-graph's writer permissions. Update the active design only
   for design-relevant learning, including what workers returned:
   - A known unknown was resolved.
   - A new known unknown appeared.
   - An implementation note changes how future work items should be built.
   - A deviation from the design as written was necessary.
   - A human decision is needed.
   Keep linked Beads current separately: file discovered execution work with `discovered-from` and,
   before a handoff or `BLOCKED`, update the bead notes with what is done, next, and any open question.
   Transferable practices follow run-execution's completion step; REFLECT does not invoke
   `run-retro` or add another reflection report.
5. REVIEW: After the integrated in-loop gate passes, apply
   [review-gate](../review-gate/SKILL.md#final-branch-review) for final whole-branch review,
   reuse, named readiness review, the simplify pass, and its PR summary. Admit any
   goal-shortfall repair through the rule above before deciding the loop outcome.
6. DECIDE:
   - Print `FINAL` only when every scoped item is closed and none is blocked, the scoped work
     satisfies agreed acceptance/UAT, the in-loop gate, full suite and final review have evidence
     at the exact integrated revision, required code review
     is `APPROVE`, any named readiness review is `READY`, and the agreed ready-for-review PR exists
     with the human's review requested. Review requirements follow review-gate.
     Record the PR URL and verification on the final review record selected by review-gate.
     Apply its review-bead closing rules.
   - Otherwise apply Stop scopes below; print `ITERATING` and fix the weakest failing point.

Hard guards follow the convention's criteria ownership, authority, and hard-stop
invariants. Apply the no-progress stop below. A repeated plan or inconclusive check
is a question for the human, not forward motion.

## Stop scopes

These stop scopes apply to bounded execution in both workflows; only the handoff uses
the loop outcomes below. A whole-execution stop prevents independent work too.

The whole handoff ends at `FINAL`, or `BLOCKED` for an exhausted whole-loop budget;
wrong or unmeetable criteria; unresolvable
scope, safety, or design ambiguity; two cycles without a code change, new verification evidence,
or resolved scope; an action outside the approved contract; a missing required capability or a PR that cannot be
opened; a failure that compromises shared state; or cancellation.

Item retry exhaustion follows [run-execution](../run-execution/SKILL.md#failure-cancellation-and-resume).
Hold affected groups and dependents under its containment rules; continue proven independent
work. End `BLOCKED` when no unblocked work remains. Keep blocked items in scope and report
their attempt trail, waiting dependents, and recommended decision.

## Building blocks

- Automation: Prefer a direct Goal-mode handoff first. Use scheduled/background automation only
  after the prompt has worked manually.
- Skill: This file is the reusable workflow wrapper.
- Sub-agents: Follow run-execution's role routing, assignments, and review rules.
  Use an explorer for unclear codepaths.
- Connectors: Use available environment and MCP/plugin connectors directly for project context such
  as issue trackers, GitHub, browser checks, docs, or telemetry.
- Verifier: The `verifier` role runs the once-only in-loop gate and returns evidence — the commands
  run, their real output, and a pass/fail — not a pass opinion. Prefer automated commands, tests,
  builds, type checks, lint checks, screenshots, or metrics. The gate is tiered: the fast in-loop
  tier must pass for `FINAL`, and the full suite runs at the review surface. Evidence belongs to the
  commit and environment it was produced for; an unchanged, deterministic gate may reuse it rather
  than re-run. If no gate exists, record the verification gap in the active design doc or ask the user.

## Loop prompt

Start the handoff in the agent harness's Goal mode with
[`templates/handoff-prompt.md`](templates/handoff-prompt.md), filling in the design-doc path and linked
bead. It restates the protocol above in prompt form because the handoff runs from that text, not
from this file.

## Completion criteria

Finish with the scoped work complete or clearly blocked, verification evidence or a named
verification gap, design-relevant learning reflected into the active design doc, and bead state
updated only for execution facts when a bead is linked. An open linked bead records what is done,
next, and any open question before handoff. A successful automation handoff ends with the agreed
ready-for-review PR and the human's review requested; the
PR body carries the audience-safe `Verification` section described in `manage-work-graph`.
Preserve the [verifier's evidence kinds](../../agents/verifier.md) in that section;
acceptance follows [Run Execution's evidence and exemption rules](../run-execution/references/execution-record.md#integration-groups-and-recovery).
Follow the convention's human gates and manage-work-graph's closure boundary.
Do not poll for merge or add retrospective checkpoints or another reflection report.
