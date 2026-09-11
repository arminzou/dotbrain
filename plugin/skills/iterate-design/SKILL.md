---
name: iterate-design
description: Iterates from an active design doc using the coding agent's native loop mode for an explicit automation handoff with a mechanical verifier and hard stop.
disable-model-invocation: true
---

# Iterate Design

Use the coding agent's native loop primitive (`/goal`, `/loop`, automation, or repeated turns).
Do not build or invoke a dotbrain loop runner. dotbrain supplies context, state boundaries, and
reflection rules; the coding agent runs the loop.

## When to use

This loop is human-triggered: the human explicitly hands off to it as an automation handoff (for
example via `/iterate-design`), and it runs on a dedicated branch — never directly on `main`.

Use when:

- Work has an active design doc in `.brain/designs/`.
- The task needs more than one ordinary turn but has a verifiable stopping condition.
- A linked bead or epic exists, or the user explicitly points at a design doc.

Do not use for one-off fixes, pure triage, open-ended brainstorming, or work without a verification
story. Reach for `operate-execution`, `find-unknowns`, `grill-decisions`, or `to-design` first.

### Loop-worthiness check

Before starting the loop, confirm all four hold. If any is missing, stay in ordinary turns instead:

1. A mechanical gate exists or can be named (a command, test, build, or metric — not just "looks right").
2. The agent can run what it changes (execute the verifier itself, not wait on an external process).
3. A hard stop is set (a retry cap or budget the loop will actually honor).
4. The preflight contract below covers the only permitted delivery action; every other irreversible
   action still has a human gate.

## Preflight contract

Before changing code, present this contract and wait for the human's explicit `GO`:

- **Scope:** one named work bead, or every implementation bead under the named design/epic in
  dependency order. An epic is never claimed merely because it anchors the scope.
- **Branch and base:** dedicated branch name and base branch.
- **Verification:** narrow checkpoint check, one full Success Criteria gate, and selected final
  `review-gate` mode (`code` by default; `simplify` or `readiness` only when named).
- **Delivery:** draft-PR authorization, plus the available provider and authenticated account.

`GO` authorizes implementation, the agreed verification, pushing the dedicated branch, and creating
the draft PR. It does not authorize merge, deploy, publish, dependency changes, or changing scope,
acceptance, or success criteria. Missing provider/auth or an unconfirmed contract is a stop before
the loop starts.

## Worktree preparation

A dedicated branch may run in place or in a git worktree. Before planning in a worktree, verify
that `.brain` and `.beads` resolve through the main checkout. When they are absent, use
`wire-brain`'s worktree repair branch before dispatch. `dotbrain wire` attaches an adopter repo to a
Brainspace; it is not the worktree repair command.

## Read order

Before planning, read:

1. The hook-injected `bd prime` protocol on a new session or after context recovery; run `bd prime`
   only when it was not injected.
2. Nearest `AGENTS.md`.
3. `.brain/CONTEXT.md`, if present.
4. The active design doc.
5. Linked bead or epic, if present: inspect `bd ready --json --quiet`, `bd human list --json --quiet`,
   and `bd show <id> --json --quiet`. Claim only an unclaimed, ready work bead with
   `bd update <id> --claim --json --quiet`; do not claim an epic merely because it is linked.
6. Relevant `.brain/docs/` references or code files only as needed.

## Controlling instruction document

Treat the active design doc as the loop's controlling instruction document.

It defines objective, scope, non-goals, constraints, the design, known unknowns, success criteria,
and where design-relevant discoveries belong.

If the design doc lacks a `Success Criteria` section, first propose the smallest useful one. If verification is human/product judgment rather than an automated command, state that and
treat it as a human decision gate.

For design/epic scope, repeat the ready-frontier check after closing each scoped implementation bead
and claim the next ready one. Do not claim the final review bead until every scoped implementation
bead has closed; `review-gate` then owns that final record.

## Loop protocol

Use this protocol inside the agent-native loop:

1. PLAN: Reread the active design doc fresh — do not rely on an earlier iteration's memory of it,
   since long runs are where constraints silently drop out of lossy context. Then pick the
   smallest checkpoint that advances the design.
2. DO: Implement only that checkpoint.
3. VERIFY: Run the smallest relevant verifier for that checkpoint, or explain why no automated
   verifier exists. Reserve the full Success Criteria gate for once, before final review.
4. REFLECT: Update the active design doc only for design-relevant learning:
   - A known unknown was resolved.
   - A new known unknown appeared.
   - An implementation note changes how future slices should be built.
   - A deviation from the design as written was necessary.
   - A human decision is needed.
   Keep linked Beads current separately: file discovered execution work with `discovered-from` and,
   before a handoff or `BLOCKED`, update the bead notes with what is done, next, and any open question.
5. REVIEW: Once the full Success Criteria gate passes, run the preflight-selected `review-gate`
   mode. The reviewer supplements the verifier, never replaces it — a review pass without a
   mechanical pass/fail check is two optimists agreeing.
6. DECIDE:
   - Print `FINAL` only when the scoped work satisfies acceptance, the full gate and final review
     have evidence, and the agreed draft PR exists. Create or update the review bead with the PR
     URL and verification, add its `human` label, and leave it open for the human gate.
   - This loop is an automation handoff: it runs on its dedicated branch, never `main`, and the
     landing path was fixed at handoff — it stays on the branch even if a mid-loop
     human-in-the-loop moment pulls the human in along the way.
   - The explicit preflight `GO` authorizes only pushing the dedicated branch and creating the
     draft PR. Merge and every other outward action remain human-owned.
   - Print `BLOCKED` and ask the user when scope, safety, or design ambiguity prevents progress.
   - Print `BLOCKED` with the attempt trail after 3 consecutive failed VERIFY cycles on the same
     checkpoint. Do not keep iterating past the cap.
   - Print `BLOCKED` after two cycles without a code change, new verification evidence, or resolved
     scope; report the stalled question rather than spending more turns.
   - Otherwise print `ITERATING` and fix the weakest failing point next.

Two hard guards:

- The verifier is not yours to change. Never edit `Success Criteria` in the design
  doc or acceptance criteria on the linked bead from inside the loop. If the criteria are wrong,
  ambiguous, or unmeetable, that is a human decision: print `BLOCKED` and say why.
- The retry cap is a stop condition, not a suggestion. A loop that only stops on success runs until
  it breaks or drains the budget.
- The no-progress cap is also a stop condition. A repeated plan or inconclusive check is a question
  for the human, not forward motion.

## Building blocks

- Automation: Prefer a manual agent-native loop first. Use scheduled/background automation only
  after the prompt has worked manually.
- Skill: This file is the reusable workflow wrapper.
- Sub-agents: Use an explorer for unclear codepaths, an implementer for scoped changes, and a
  reviewer/checker before finalizing meaningful changes. Do not let the implementer be the only
  judge of correctness.
- Connectors: Use available environment and MCP/plugin connectors directly for project context such
  as issue trackers, GitHub, browser checks, docs, or telemetry.
- Verifier: Prefer automated commands, tests, builds, type checks, lint checks, screenshots, or
  metrics. If none exists, record the verification gap in the active design doc or ask the user.

## Loop prompt

Paste [`templates/loop-prompt.md`](templates/loop-prompt.md) into the agent's native loop mode,
filling in the design-doc path and linked bead. It restates the protocol above in prompt form
because the loop runs from that text, not from this file.

## Completion criteria

Finish with the scoped work complete or clearly blocked, verification evidence or a named
verification gap, design-relevant learning reflected into the active design doc, and bead state
updated only for execution facts when a bead is linked. An open linked bead records what is done,
next, and any open question before handoff. A successful automation handoff ends with the agreed
draft PR and an open `human`-labeled review bead; the PR body carries the audience-safe
`Verification` section described in `operate-execution`.
