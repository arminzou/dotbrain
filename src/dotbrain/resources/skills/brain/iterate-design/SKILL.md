---
name: iterate-design
description: Iterate from an active design doc using the coding agent's native loop mode. Use when feature work should repeatedly plan, implement, verify, reflect design-relevant learning, and stop on a clear success or blocked condition.
---

# Iterate Design

Use the coding agent's native loop primitive (`/goal`, `/loop`, automation, or repeated turns).
Do not build or invoke a dotbrain loop runner. dotbrain supplies context, state boundaries, and
reflection rules; the coding agent runs the loop.

## When to Use

This loop is human-triggered: the human explicitly hands off to it as an automation handoff (for
example via `/iterate-design`), and it runs on a dedicated branch — never directly on `main`.

Use when:

- Work has an active design doc in `.brain/designs/`.
- The task needs more than one ordinary turn but has a verifiable stopping condition.
- A linked bead or epic exists, or the user explicitly points at a design doc.

Do not use for one-off fixes, pure triage, open-ended brainstorming, or work without a verification
story. Use `operate-execution`, `find-unknowns`, `grill-decisions`, or `to-design` first.

### Loop-worthiness check

Before starting the loop, confirm all four hold. If any is missing, stay in ordinary turns instead:

1. A mechanical gate exists or can be named (a command, test, build, or metric — not just "looks right").
2. The agent can run what it changes (execute the verifier itself, not wait on an external process).
3. A hard stop is set (a retry cap or budget the loop will actually honor).
4. A human gate covers anything irreversible the loop's checkpoints might touch.

## Read Order

Before planning, read:

1. Nearest `AGENTS.md`.
2. `.brain/CONTEXT.md`, if present.
3. The active design doc.
4. Linked bead or epic, if present.
5. Relevant `.brain/docs/` references or code files only as needed.

Use `CONTEXT.md` vocabulary exactly. Do not invent synonyms for established project concepts.

## Controlling Instruction Document

Treat the active design doc as the loop's controlling instruction document.

It defines objective, scope, non-goals, constraints, current design, known unknowns, verification /
success criteria, and where design-relevant discoveries belong.

If the design doc lacks verification criteria, first propose the smallest useful verification
section. If verification is human/product judgment rather than an automated command, state that and
treat it as a human decision gate.

## Loop Protocol

Use this protocol inside the agent-native loop:

1. PLAN: Reread the active design doc fresh — do not rely on an earlier iteration's memory of it,
   since long runs are where constraints silently drop out of lossy context. Then pick the
   smallest checkpoint that advances the design.
2. DO: Implement only that checkpoint.
3. VERIFY: Run the verifier named by the design doc, or explain why no automated verifier exists.
4. REFLECT: Update the active design doc only for design-relevant learning:
   - A known unknown was resolved.
   - A new known unknown appeared.
   - An implementation note changes how future slices should be built.
   - A deviation from the current design was necessary.
   - A human decision is needed.
5. REVIEW: When implementation and verification pass, use a checker/reviewer subagent if available
   and the change is non-trivial. The reviewer supplements the verifier, never replaces it — a
   review pass without a mechanical pass/fail check is two optimists agreeing.
6. DECIDE:
   - Print `FINAL` only when the checkpoint satisfies acceptance and verification evidence exists.
     `FINAL` means the checkpoint is verified, not that the work has landed — do not stop silently
     with verified work sitting unlanded on a branch.
   - This loop is an automation handoff: it runs on its dedicated branch, never `main`, and the
     landing path was fixed at handoff — it stays on the branch even if a mid-loop
     human-in-the-loop moment pulls the human in along the way.
   - Landing means opening the review surface: a PR when the project hosts them, otherwise the
     branch diff reviewed directly and merged locally. Opening the review surface is an
     outward-facing action, so the loop ends and hands to the human for that action — never push
     or open a PR unprompted.
   - Print `BLOCKED` and ask the user when scope, safety, or design ambiguity prevents progress.
   - Print `BLOCKED` with the attempt trail after 3 consecutive failed VERIFY cycles on the same
     checkpoint. Do not keep iterating past the cap.
   - Otherwise print `ITERATING` and fix the weakest failing point next.

Two hard guards:

- The verifier is not yours to change. Never edit `Verification / Success Criteria` in the design
  doc or acceptance criteria on the linked bead from inside the loop. If the criteria are wrong,
  ambiguous, or unmeetable, that is a human decision: print `BLOCKED` and say why.
- The retry cap is a stop condition, not a suggestion. A loop that only stops on success runs until
  it breaks or drains the budget.

## Building Blocks

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

## Prompt Skeleton

```text
Use your native goal/loop mode.

Active design doc:
<path>

Linked bead:
<id or none>

Treat the active design doc as the controlling instruction document for this loop.

Objective:
Implement the smallest coherent checkpoint that advances this design.

Stopping condition:
Stop when the checkpoint satisfies the design doc's Verification / Success Criteria, relevant checks
pass, design-relevant discoveries are reflected into the active design doc, and reviewer feedback has
no blocking findings.

Loop protocol (every iteration, not just the first):
1. Reread the active design doc fresh, plus AGENTS.md, CONTEXT.md if present, and the linked bead
   if present. Do not rely on an earlier iteration's memory of the design doc.
2. Pick the next smallest checkpoint.
3. If the path is unclear, use a read-only explorer first.
4. Implement only the checkpoint.
5. Run the verifier named in the design doc.
6. If the verifier fails, make the smallest targeted fix and retry. After 3 consecutive failed
   verify cycles on the same checkpoint, stop and report BLOCKED with the attempt trail.
7. If design-relevant learning appears, update Known Unknowns, Implementation Notes, Deviations, or
   Human Decisions Needed in the active design doc.
8. If implementation and verification pass, use a reviewer/checker before FINAL when available. The
   reviewer supplements the verifier, never replaces it — a review pass without a mechanical
   pass/fail check is two optimists agreeing.
9. Stop if blocked by missing design guidance, unsafe scope growth, or verifier ambiguity.
10. Before calling FINAL: this loop is an automation handoff running on its dedicated branch
    (never `main`). The landing step is opening the review surface — a PR when the project hosts
    them, otherwise the branch diff reviewed directly and merged locally — and that landing path
    stays fixed even if a mid-loop human-in-the-loop moment pulls the human in.

Progress log:
- Current checkpoint
- What changed
- What was verified
- What remains
- Whether blocked

Rules:
- Do not expand scope beyond the design doc.
- Do not turn the design doc into a task checklist.
- Keep execution state in beads.
- Keep design learning in the active design doc.
- Do not call FINAL without verifier evidence.
- Never edit Verification / Success Criteria or bead acceptance criteria; if they are wrong or
  unmeetable, report BLOCKED instead.
- Never iterate past 3 consecutive failed verify cycles on the same checkpoint.
- FINAL is not landing. This automation-handoff loop lands through the review surface — a PR
  when the project hosts them, otherwise a branch diff reviewed directly and merged locally —
  and that landing path stays fixed on the branch even if the human is pulled in mid-loop.
- Never push or open a PR unprompted — opening the review surface is the human's action to take
  or authorize.
```

## Completion Criteria

Finish with checkpoint complete or clearly blocked, verification evidence or a verification gap,
design-relevant learning reflected into the active design doc, and bead state updated only for
execution facts when a bead is linked.

Checkpoint-verified is not landed. This automation-handoff loop runs on its dedicated branch,
never `main`, and lands through the review surface — a PR when the project hosts them, otherwise
the branch diff reviewed directly and merged locally. Opening that review surface is an
outward-facing action: do not push or open it without the user present to authorize it. The
landing path was fixed at handoff and stays on the branch even if a mid-loop human-in-the-loop
moment pulls the human in.

When the checkpoint lands through a public PR, the PR body must carry a `Verification` section
restating the evidence (commands run, results, screenshots, metric values) in audience-safe,
plain terms. No `.brain/` paths, ADR numbers, or `design:` spec-ids in the PR body — the design
doc holds the private, durable record; the PR holds the public, per-change rendering.
