---
pageClass: prompt-examples
---

# Example Prompts

You use dotbrain mostly by asking your coding agent to do things. This page collects prompts you
can send as they are, or adapt, for the common jobs. Each one says when to use it, which skill it
triggers, and where the step is explained.

You do not have to name a skill: describing the job is usually enough for the agent to pick it.
Naming the skill makes the choice certain. Two skills, `iterate-design` and `review-architecture`,
never start on their own; invoke them explicitly, for example `/dotbrain:iterate-design` in Claude
Code.

## Set Up

### Wire a repo

```text
Use wire-brain to wire this repo with Dotbrain.
```

**When:** the first time you use dotbrain in a repo, or in a new worktree. Installs the CLI and
its prerequisites if needed. **Skill:** `wire-brain`. See [Getting started](getting-started.md).

### Repair the wiring

```text
dotbrain doctor reports problems in this repo. Use wire-brain to find out why and repair the wiring.
```

**When:** `.brain` or `.beads` is missing, links dangle, or the agent does not know the project.
Also after a plugin or CLI update. **Skill:** `wire-brain`. See [Wiring](wiring.md) and
[Troubleshooting](troubleshooting.md).

## Plan

### Get oriented in unfamiliar code

```text
Run find-unknowns on how GET /orders handles queries and responses before we add pagination.
```

**When:** before touching code you do not know, or at the start of an initiative. Read-only; it
reports assumptions and constraints that would change your approach. **Skill:** `find-unknowns`.
See [The workflow](workflow.md#_1-orient).

### Settle decisions

```text
Grill me on this plan: add pagination to GET /orders so clients can fetch orders in smaller batches.
Help me settle the pagination approach, default page size, and compatibility with existing clients.
Check it against our vocabulary and existing ADRs, and record what we settle.
```

**When:** you have a plan with open questions or terms that need sharpening. Settled terms go into
`CONTEXT.md`, hard-to-reverse choices into `adr/`. **Skill:** `grill-decisions`. See
[The workflow](workflow.md#_2-settle-decisions).

### Write a design

```text
Write a design for orders API pagination, with success criteria and known unknowns.
```

**When:** the work spans several sessions, crosses modules, or carries real unknowns. Creates a
design doc in `.brain/designs/` and a tracking epic. **Skill:** `to-design`. See
[The workflow](workflow.md#_3-write-the-design).

### Split a design into issues

```text
Split the orders-pagination design into issues with acceptance criteria and dependencies.
```

**When:** the design is settled and approved. Runs once per design. **Skill:** `to-issues`. See
[The workflow](workflow.md#_4-split-into-issues).

## Work

See [Working with an agent team](agent-team.md) for workflow choices, ownership, and coordination.

Choose a **workflow** and an **execution mode** separately. **HITL** (Human-in-the-Loop)
returns to you after each bounded execution; **handoff** continues within a contract you approve.
**Sequential** means one agent changes code at a time; **parallel** means multiple workers change
code at once. Read-only research, review, or verification does not make execution parallel.
See [The workflow](workflow.md#_5-work-the-issues).

### Track work

```text
What's ready to work on?
```

```text
File an issue: GET /orders returns duplicate orders on the next page. Link it to the orders-pagination epic.
```

**When:** you want to see the ready frontier, or file, claim, update, or close an issue.
**Skill:** `manage-work-graph`. See [The workflow](workflow.md#_5-work-the-issues).

### HITL: sequential execution

::: info Default workflow and execution mode
HITL with sequential execution is the default. You can ask for the next issue without naming
either setting; the agent returns to you after that bounded execution.
:::

```text
Work the next ready issue under the orders-pagination epic.
```

**When:** you want to direct one bounded execution at a time. The lead may write the change or
delegate to one `worker`; either is sequential. Behavior changes get independent review.
**Skill:** `run-execution`. See [The workflow](workflow.md#_5-work-the-issues).

### HITL: parallel execution

::: info Default worker cap
Parallel execution allows up to two workers at once by default, in either workflow.
You only need to specify a worker cap in the prompt when you want to change it.
:::

```text
Work the ready issues under the orders-pagination epic in parallel where they are independent. Show me the branch and how you'll split the work before starting.
```

**When:** independent issues are ready together and you want to direct the batch. If safe parallel
execution is unavailable, the agent reports that and falls back to sequential execution.
**Skill:** `run-execution`. See [The workflow](workflow.md#_5-work-the-issues).

### Handoff: sequential execution

```text
/dotbrain:iterate-design Work the orders-pagination design, one issue at a time. Propose the handoff contract and wait for my GO.
```

**When:** the design is active, the work has a mechanical check, and you want the agent to carry
on without you. It proposes a contract (scope, branch, checks, worker count, pull request
delivery) and starts only after you reply `GO`. Merging stays with you. **Skill:**
`iterate-design`, explicit only. See [The workflow](workflow.md#_5-work-the-issues).

### Handoff: parallel execution

```text
/dotbrain:iterate-design Work the orders-pagination design, taking independent issues in parallel. Propose the handoff contract and wait for my GO.
```

**When:** you want the agent to continue through an active design and parallelize independent work.
An item that exhausts its retries or needs your decision waits with its dependents; independent
items continue. A handoff with any blocked scoped item cannot finish successfully or mark its PR ready.
**Skill:** `iterate-design`, explicit only. See [The workflow](workflow.md#_5-work-the-issues).

For either handoff mode, the approved `GO` authorizes pushing the dedicated branch, a draft PR
at the first push, and a ready PR with your review requested after successful verification and
review. Merge, deployment, publication, dependency changes, and changes to scope or success
criteria still need your decision.

## Packaged Subagents

See [The packaged subagents](agent-team.md#the-packaged-subagents) for their responsibilities and runtime behavior.

Skills describe the workflow; subagents take focused assignments from your main agent. Ask your
main agent to delegate using these names:

| Role | Claude Code | Codex |
|---|---|---|
| Writing | `dotbrain:worker` | `dotbrain-worker` |
| Research | `dotbrain:researcher` | `dotbrain-researcher` |
| Review | `dotbrain:reviewer` | `dotbrain-reviewer` |
| Verification | `dotbrain:verifier` | `dotbrain-verifier` |

The prompts below name the role; use the runtime name above if needed. These are subagent
assignments, not slash commands. See [Session context](session-context.md#subagents).

### Delegate one change to a worker

```text
Have the worker fix duplicate orders across pages in GET /orders on our current branch. Give it the issue, its own Beads actor, and the agreed checks. Have it commit the fix and report back.
```

**When:** you have one concrete change to delegate. The `worker` writes and commits a candidate;
it never pushes, merges, or closes work items. For a tracked batch, prefer `run-execution`, which
prepares the assignments and coordinates review and integration.

### Research an API decision

```text
Ask the researcher whether cursor or offset pagination fits GET /orders better. Check our Brain, the code, and official docs, and explain the trade-offs with sources.
```

**When:** you need a sourced answer that connects project context, code, and outside evidence.
The `researcher` reports findings and proposed updates; it does not implement them.

### Get an independent review

```text
Have the reviewer check this orders-pagination branch against main and our acceptance criteria. Look for pagination bugs, authorization gaps, compatibility problems, and missing tests.
```

**When:** you want a focused review from an agent that wrote none of the change. The `reviewer`
judges the diff and surrounding code. Workflow item reviews also need the item ID, reviewer actor,
review number, candidate revision, and diff base; `run-execution` supplies that assignment.

### Run a mechanical verification gate

```text
Have the verifier run the agreed checks for orders pagination on this branch and give me the results and a Verification block for the PR.
```

**When:** you need evidence that the agreed checks pass. The `verifier` runs the gate and reports
what it observed; it does not fix failures or give a code-review opinion.

## Review and Close

### Review a change

```text
Run a code review gate on this branch against main.
```

```text
Run a simplify review on this branch: what can we delete or replace?
```

**When:** before offering a branch for merge, or whenever you want an independent review. Modes
are `code` (correctness), `simplify`, and `readiness` (is a subsystem sound enough to build on).
**Skill:** `review-gate`. See [The workflow](workflow.md#_6-review).

### Close a design

```text
The orders-pagination work is merged. Close the design: record the evidence and promote what should outlive it to ADRs and CONTEXT.md.
```

**When:** an initiative ships, is abandoned, or is superseded. Also for sweeping designs that
never closed out. **Skill:** `close-design`. See [The workflow](workflow.md#_7-close-the-design).

## Learn

### Start learning a topic

```text
Teach me how this project handles failed deliveries. I want to be able to diagnose one myself.
```

**When:** you want to understand part of the project, not just get an answer. **Skill:**
`teach-me`. See [Learning your project](learning.md).

### Continue a learning path

```text
Continue my learning path on retries. Read my progress and learning records, then resume the next step.
```

**When:** picking up learning in a new session. **Skill:** `teach-me`. See
[Learning your project](learning.md#walk-a-learning-path).

### Park a question for later

```text
Park this for learning: why does retrying this operation require an idempotency key?
```

**When:** a question comes up mid-task and you do not want to switch into teaching now.
**Skill:** `teach-me`. See [Learning your project](learning.md#park-a-question-while-working).

## Maintain the Brain

### Set up or fix the Brain site

```text
Set up a Brain site for this project and put the runbooks in the sidebar.
```

```text
dotbrain site build fails. Find the cause and fix it.
```

**When:** you want to read the Brain in a browser, rearrange its sidebar, or repair a failed build.
**Skill:** `brain-site`. See [Brain site configuration](brain-site-configuration.md).

### Check context health

```text
Check this project's context health: find stale, duplicated, or misplaced guidance across AGENTS.md and the Brain, and anything private leaking into the public repo.
```

**When:** guidance has piled up, `AGENTS.md` and `CLAUDE.md` have drifted, or you want to check the
public/private boundary. It reports by default and fixes only what you ask. **Skill:**
`curate-project-context`.

### Write or edit agent-facing docs

```text
Use write-agent-docs to tighten this project's AGENTS.md.
```

**When:** creating or editing `AGENTS.md`, Brain context, design docs, skills, or public docs agents
rely on. **Skill:** `write-agent-docs`.

### Triage public issues

```text
Triage the open GitHub issues and promote the accepted ones into our work graph.
```

**When:** the project takes public issues and you want them classified, reproduced, and brought
into private execution. Requires `public-tracker` in [`project.yaml`](configuration.md#project-yaml).
**Skill:** `triage-public`.

### Look for architecture improvements

```text
/dotbrain:review-architecture
```

**When:** you want a review of the codebase for deepening opportunities, informed by the Brain's
vocabulary and ADRs. **Skill:** `review-architecture`, explicit only.

## Related

- [Skills](skills.md) lists every skill with a one-line summary.
- [The workflow](workflow.md) shows how the skills fit together.
