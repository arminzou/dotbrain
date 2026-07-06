---
name: to-issues
description: Break a design doc into independently-workable bead tasks under an epic. Decomposes the plan into vertical-slice issues with acceptance criteria and dependencies. Use when a design doc is ready and you want to create the execution graph.
---

# To Issues

Take a design doc and decompose it into bead tasks under the epic. Each task is a thin, vertical slice that cuts through all integration layers — a demoable unit of work.

## Process

### 1. Find the design doc

If the user passes a design doc path or name, use that. Otherwise, find the latest design doc in `.brain/designs/`:

```bash
ls -t .brain/designs/*.md | head -1
```

Read the full design doc — motivation, goals, design, implementation plan, and non-goals.

### 2. Draft vertical slices

Decompose the goals and implementation plan into **vertical slices** (tracer bullets). Each slice delivers a narrow but complete path through every layer (schema, API, UI, tests if applicable). A completed slice is demoable or verifiable on its own.

Prefer many thin slices over few thick ones.

For each slice, identify:

- **Title** — short descriptive name
- **Scope** — AFK or HITL
  - **AFK** (Away From Keyboard): the agent can implement and merge without human input. These beads are NOT flagged `bd human`.
  - **HITL** (Human In The Loop): needs a decision, design review, or sign-off at some point. These beads get flagged `bd human`.
  - Prefer AFK over HITL where possible.
- **Blocked by** — which other slices (if any) must complete first
- **Goals covered** — which goals from the design doc this addresses
- **Acceptance criteria** — outcome-focused, verifiable. Self-test: if you rebuilt the solution differently, would the criteria still hold?

### 3. Present for sign-off

Present the breakdown as a numbered list. For each slice, show:

- **Title**, **Scope** (AFK/HITL), **Blocked by**, **Goals covered**, **Acceptance criteria** (brief)

Ask the user:

- Does the granularity feel right?
- Are the dependency relationships correct?
- Should any slices be merged or split?
- Are the HITL markings correct?

Iterate until the user approves.

### 4. Create the beads

Create beads in dependency order (blockers first) so the blocker IDs exist when you link:

```bash
bd create "<Slice Title>" --parent <epic-id> --type task \
  --acceptance "Criterion 1; Criterion 2" \
  --priority <priority>
```

Then link dependencies separately — `bd dep add` reads "**<from> depends on <to>**", so the
*second* argument is the prerequisite:

```bash
bd dep add <blocked-id> <blocker-id>     # <blocked> waits on <blocker>
```

Do **not** use `bd create --deps "blocks:<id>"` for this: `blocks:<id>` means "*this* issue
blocks `<id>`" — the reverse relationship — which silently inverts the whole graph. After
linking, confirm with `bd ready`: only the slices with no blockers should appear.

For HITL slices, set the human gate by adding the `human` label (there is no `bd human <id>`
flagging verb — that prints a help menu and does nothing):

```bash
bd label add <bead-id> human             # surfaced by `bd human list`
```

If the project has a public issue tracker, also create a tracking issue for each slice with a `needs-triage` label and link via `--external-ref gh-<number>`.

### 5. Close

Summarize what was created — the epic ID, the number of task beads, and any items labeled `human`. Recommend that the user review the HITL items and mark them as ready when they've made the needed decisions.

## Pitfalls

- **Do not skip the sign-off step.** The user may have valuable input on slice boundaries and dependencies.
- **Do not create beads out of dependency order.** Blockers need real IDs before you can `bd dep add <blocked> <blocker>`. Create blockers first.
- **Do not mark all slices AFK.** Be honest about what needs a human decision — it's better to over-flag early and remove the gate later than to have an agent spin on an ambiguous task.
- **Do not include implementation detail in acceptance criteria.** Keep them outcome-focused and verifiable.
