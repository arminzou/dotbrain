---
name: iterate-design
description: Iterates from an active design doc in Goal mode for an explicit automation handoff with a mechanical verifier and hard stop.
disable-model-invocation: true
---

# Iterate Design

Use the agent harness's Goal mode when available. Otherwise, keep work in the same task and
make bounded repeated turns.
Do not build or invoke a dotbrain loop runner. dotbrain supplies context, state boundaries, and
reflection rules; the coding agent runs the loop.

## When to use

This loop drives the handoff workflow and is human-triggered: the human explicitly hands off to it as an automation handoff (for
example via `/iterate-design`), and it runs on a dedicated branch — never directly on `main`.

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

Before changing code, present this contract and wait for the human's explicit `GO`:

- **Scope:** one named work bead, or every implementation bead under the named design/epic in
  dependency order. An epic is never claimed merely because it anchors the scope.
- **Branch and base:** dedicated branch name, a short slug with no work-item ID, and base branch.
- **Verification:** the narrow checkpoint check (run in this session, by whoever made the change);
  one in-loop Success Criteria gate — the fast tier that must pass for `FINAL`; the full suite at
  the review surface; final whole-branch `code` review for a multi-item branch, plus the default
  non-blocking `simplify` pass; `readiness` only when the handoff contract names it.
- **Workers:** the writing-worker cap for each bounded execution (2 by default).
- **Human gates:** every human-gated item in the proposed scope. A handoff that includes one can
  only end `BLOCKED`, so the human sees that before `GO`.
- **Delivery:** authorize the Handoff delivery sequence below. Confirm the provider and auth, a
  base-branch ruleset requiring a reviewed PR and dismissing stale approvals, and an agent
  identity distinct from the human reviewer; mentions and review requests come from that agent
  identity.

`GO` authorizes implementation, the agreed verification, pushing the dedicated branch, opening a
draft PR at the first push, one mention of the human for each blocked stop, and marking the PR
ready with the human's review requested at `FINAL`. It does not authorize merge, deploy, publish,
dependency changes, or changing scope, acceptance, or success criteria. Missing provider/auth,
agent identity, required ruleset, or an unconfirmed contract is a stop before the loop starts.

## Handoff delivery

After the first item integrates and passes its integrated check, push the dedicated branch and
open a draft PR at the first push. Record its URL in the private execution record and the active
design, and attach it in the runtime where supported. Do not create a placeholder commit to open
it at preflight. Push after each integrated item that passes its integrated check. The pushed
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
preserves its registration. For delegated worker checkouts, follow `run-execution`'s applicable
runtime reference: Claude subagent worktrees use absolute assignment references without wiring;
the Codex CLI path attaches prepared worktrees before launch to deliver project resources.

## Read order

Before planning, read:

1. `bd prime` on a new session or after context recovery. dotbrain injects no Beads context; skip
   it only when the operator's own Beads hook already supplied it.
2. Nearest `AGENTS.md`.
3. `.brain/CONTEXT.md`, if present.
4. The active design doc.
5. Linked bead or epic, if present: inspect `bd ready --json --quiet`, `bd human list --json --quiet`,
   and `bd show <id> --json --quiet`. Claim only when you will work the item yourself as a team of
   one; when workers will be dispatched, leave the claim to `run-execution`'s Dispatch and claim
   step, which claims under each worker's own actor. Never claim an epic merely because it is linked.
6. Relevant `.brain/docs/` references or code files only as needed.

## Controlling instruction document

Treat the active design doc as the loop's controlling instruction document.

It defines objective, scope, non-goals, constraints, the design, known unknowns, success criteria,
and where design-relevant discoveries belong.

If the design doc lacks a `Success Criteria` section, first propose the smallest useful one. If verification is human/product judgment rather than an automated command, state that and
treat it as a human decision gate.

For design/epic scope, repeat the ready-frontier check after closing each scoped implementation bead
and select the next ready one for `run-execution`. Do not claim the final review bead until every
scoped implementation bead has closed; `review-gate` then owns that final record.

## Loop protocol

Use this protocol throughout the handoff:

1. PLAN: Reread the active design doc fresh — do not rely on an earlier iteration's memory of it,
   since long runs are where constraints silently drop out of lossy context. Then select the next
   bounded execution: one ready work item or a finite batch of ready items within the approved
   scope. Never add items silently to an execution already under way.
2. DO: Run that bounded execution through `run-execution`, as its lead. This skill keeps the
   outer loop, reflection, overall limits, final review, and delivery.
3. VERIFY: The agent that made a change runs its checkpoint check, inside `run-execution`; never
   spawn an agent just to check a checkpoint. Reserve the once-only in-loop gate for before final
   review.
4. REFLECT: As the lead, the only agent that edits the active design doc, update it only for
   design-relevant learning, including what workers returned:
   - A known unknown was resolved.
   - A new known unknown appeared.
   - An implementation note changes how future work items should be built.
   - A deviation from the design as written was necessary.
   - A human decision is needed.
   Keep linked Beads current separately: file discovered execution work with `discovered-from` and,
   before a handoff or `BLOCKED`, update the bead notes with what is done, next, and any open question.
5. REVIEW: After the integrated in-loop gate passes, run `review-gate`'s final whole-branch
   `code` review for a branch carrying more than one work item, against its base, by a fresh
   reviewer that ran none of the item reviews. Check interactions, consistency, and conformance
   to the active design doc; do not reopen approved item findings. Record the design-level
   review bead. A single-item branch skips it: its item review is the final code review. Run
   `readiness` only when the handoff contract names it, in addition to code review.
   Run a non-blocking `simplify` pass beside final code review, also for single-item branches.
   Record its findings in a separate review bead under the epic. Never apply simplify findings
   in-loop; they never block the PR or `FINAL`. When its engine is unavailable, skip with a note.
   The PR body adds one line: "N non-blocking simplification suggestions", with no finding
   details, or a one-line skip note. Review supplements the verifier, never replaces it.
6. DECIDE:
   - Print `FINAL` only when every scoped item is closed and none is blocked, the scoped work
     satisfies acceptance, the in-loop gate and final review have evidence, required code review
     is `APPROVE`, any named readiness review is `READY`, and the agreed ready-for-review PR exists
     with the human's review requested. A skipped or findings-bearing simplify pass does not
     prevent `FINAL`.
     Record the PR URL and verification on the design-level code review bead, add its `human`
     label, and leave it open for the human gate. A single-item branch has no such bead: record
     them on its work item instead.
   - This loop is an automation handoff: it runs on its dedicated branch, never `main`, and the
     landing path was fixed at handoff — it stays on the branch even if a mid-loop
     return to the human is needed along the way.
   - Among outward actions, the explicit preflight `GO` authorizes only the Handoff delivery
     sequence above. Merge and every other outward action remain human-owned.
   - Apply the two stop scopes in Stop scopes below: item-level retry exhaustion or a human gate
     blocks that item and its dependents, not independent work. Print `BLOCKED` immediately for a
     whole-handoff condition, or when no unblocked work remains. Do not retry a blocked item without human
     authorization; preserve its attempt trail.
   - Print `BLOCKED` after two cycles without a code change, new verification evidence, or resolved
     scope; report the stalled question rather than spending more turns.
   - Otherwise print `ITERATING` and fix the weakest failing point next.

Hard guards:

- The verifier is not yours to change. Never edit `Success Criteria` in the design
  doc or acceptance criteria on the linked bead from inside the loop. If the criteria are wrong,
  ambiguous, or unmeetable, that is a human decision: print `BLOCKED` and say why.
- The retry cap is a stop condition, not a suggestion. A loop that only stops on success runs until
  it breaks or drains the budget.
- The no-progress cap is also a stop condition. A repeated plan or inconclusive check is a question
  for the human, not forward motion.

## Stop scopes

The whole handoff ends at `FINAL`, or `BLOCKED` for wrong or unmeetable criteria; unresolvable
scope, safety, or design ambiguity; two cycles without a code change, new verification evidence,
or resolved scope; an action outside `GO`; a missing required capability or a PR that cannot be
opened; a failure that compromises shared state; or cancellation.

An item blocks after 3 consecutive failed checks on one checkpoint, 3 consecutive item-review
`CHANGES`, or a human gate. Only that item and its dependents stop; independent items continue.
End the handoff `BLOCKED` once no unblocked work remains. Report every blocked item with its
attempt trail and a recommended decision, including waiting dependents. Never mark a PR ready
while any scoped item is blocked. Keep blocked items in the fixed scope; do not drop them to
claim success. The HITL workflow instead pauses new dispatch and integration and asks the human.

## Building blocks

- Automation: Prefer a direct Goal-mode handoff first. Use scheduled/background automation only
  after the prompt has worked manually.
- Skill: This file is the reusable workflow wrapper.
- Sub-agents: Use an explorer for unclear codepaths. `run-execution` dispatches the packaged worker,
  in the lead's checkout or in its own worktree as the lead instructs. The agent that makes
  a change runs that checkpoint's check; the `verifier` role is reserved for the
  once-only in-loop gate, and a reviewer supplements the gate before finalizing meaningful changes.
  Do not let the worker be the only judge of correctness.
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
ready-for-review PR, the human's review requested, and an open `human`-labeled review bead; the
PR body carries the audience-safe `Verification` section described in `manage-work-graph`.
