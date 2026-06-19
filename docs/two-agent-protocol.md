# Two-Agent Protocol

The two-agent protocol is optional. Single-agent execution is the default.

Use the two-agent setup when one session should stay parked on the main checkout as the review and
merge station, while another session does the implementation work in an isolated worktree.

## Roles

There are two roles:

- `main-agent`
  Stays on the main checkout, inspects ready work, dispatches a slice, reviews the result, and lands it.
- `worker`
  Works in a separate dotbrain-wired worktree and owns the implementation for the selected slice.

The split is about coordination, not about creating a second planning system. The private execution
graph remains the source of truth.

## When To Use It

Use the two-agent protocol when:

- the work is large enough that review and landing should stay separate from implementation
- you want worktree isolation for a slice without losing access to the same Brain and execution state
- one session should stay focused on triage, review, or merge decisions while another edits code

Stay single-agent when the work is small, local, or not worth the handoff overhead.

## Concurrency Contract

`bd ready` is the concurrency contract.

The ready frontier is the set of open items with no open blockers. That is the safe pool for
parallel pickup. The two-agent protocol does not replace this rule; it only changes how one chosen
slice is coordinated.

## Worktrees

The worker runs in a git worktree, but it does not get a separate Brain or separate execution store.

Main checkout and worker worktrees share the same private Brainspace wiring:

- `.brain`
- `.beads`
- `.claude`
- `.codex`

That means the worker sees the same Brain context and the same live execution state as the
main-agent session.

## Landing Spectrum

Landing can happen in more than one way:

- PR merge
- local merge after branch CI
- pure local merge

The main-agent session owns that decision and performs the review and landing step.

## Skill Ownership

Two skills define this workflow:

- [skills.md](/home/armin/repos/projects/dotbrain/docs/skills.md) documents the packaged skill set
- `operate-execution` chooses the ready work and recommends whether it should stay in the current session or move to worktree execution
- `enter-main-agent` covers the optional coordination mode where the main checkout becomes the review and merge station

## Rule Of Thumb

Treat the two-agent protocol as an opt-in coordination pattern for bigger slices. Do not use it by
default, and do not treat it as a replacement for the execution graph.
