---
name: to-prd
description: Turn the current conversation context into a PRD, save it to the Brain, and create an epic bead. Use when the user wants to formalize a multi-step initiative before decomposing into work items.
---

# To PRD

Synthesize the current conversation context and codebase understanding into a Product Requirements Document. The PRD lives in the Brain as a durable reference; the epic bead tracks execution.

Do NOT interview the user — synthesize what you already know from the conversation. If you need architecture or module-level clarity, explore the codebase.

## Process

### 1. Gather context

Read the existing Brain context for this project:

1. `.brain/CONTEXT.md` — domain vocabulary; use it throughout the PRD
2. `.brain/adr/` — relevant decisions in the area you're touching
3. Existing `.brain/prd/` — check for related PRDs

### 2. Explore the codebase

If you haven't already, explore the codebase to understand the current state. Sketch the major modules you will need to build or modify.

Actively look for opportunities to extract **deep modules** — ones that encapsulate a lot of functionality in a simple, testable interface which rarely changes (as opposed to shallow modules that are thin wrappers or pass-throughs).

Present the module sketch to the user and confirm expectations before proceeding.

### 3. Write the PRD

Save the PRD to `.brain/prd/<feature-slug>.md`. Use a short kebab-case slug that captures the initiative (e.g., `workflow-automation.md`, `api-rate-limiting.md`).

<prd-template>

## Problem Statement

The problem the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A numbered list of user stories. Each story should be in the format:

1. As an `<actor>`, I want a `<feature>`, so that `<benefit>`

Be extensive — cover all aspects of the feature. These stories will be decomposed into bead tasks.

## Out of Scope

What is explicitly not part of this initiative.

## Further Notes

Any additional context, risks, or open questions.

</prd-template>

### 4. Create the epic bead

Create an epic bead for this initiative:

```bash
bd create "<PRD title>" --type epic --description "See .brain/prd/<slug>.md" --spec-id prd:<slug>
```

The `--spec-id` link points from beads to the spec document. If a public issue tracker is configured, also create a tracking issue there with a `needs-triage` label and link it via `--external-ref`.

### 5. Close

Summarize what was created — the PRD path and the epic bead ID — and recommend the next step (running `to-issues` to decompose into task beads).

## Pitfalls

- **Do not include implementation details like file paths or code snippets in the PRD.** They go stale quickly. Keep the PRD at the problem/solution/story level.
- **Do not skip the module sketch step for unfamiliar codebases.** The decomposition depends on understanding the module boundaries.
- **Do not create the epic bead before the user confirms the module sketch.** The sketch validates the scope.
