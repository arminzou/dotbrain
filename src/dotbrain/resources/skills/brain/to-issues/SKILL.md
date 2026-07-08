---
name: to-issues
description: Break a design doc into independently-workable bead tasks under an epic. Decomposes the plan into vertical-slice issues with acceptance criteria and dependencies. Use when a design doc is ready and you want to create the execution graph.
---

# To Issues

Take a design doc and decompose it into bead tasks under the epic. Each task is a thin, vertical
slice that cuts through all integration layers - a demoable unit of work. The design doc remains
the initiative-level design authority; beads carry execution.

## Process

### 1. Find the design doc

If the user passes a design doc path or name, use that. Otherwise, find the latest design doc in
`.brain/designs/`:

```bash
ls -t .brain/designs/*.md | head -1
```

Read the full design doc, especially `Goals`, `Current Design`, `Known Unknowns`,
`Implementation Notes`, `Deviations`, and `Non-goals`.

### 2. Draft vertical slices

Decompose the goals and implementation notes into vertical slices. Each slice should deliver a
narrow but complete path through every relevant layer. A completed slice should be demoable or
otherwise verifiable on its own.

Sequence the slices by volatility: within their dependency constraints, put the ones that resolve the
most volatile, highest-blast-radius decisions — data models, type interfaces, migration shape — first.
Validating a risky assumption in the first slice is far cheaper than discovering it wrong in the fifth.

Word each slice `Title` to echo the corresponding `Current Design` subsection heading or a
distinctive phrase from it. This lets a later reader match a bead straight back to its exact
design-doc section by title alone, without re-reading the whole document.

For each slice, show:

- `Title`
- `Scope` (`AFK` or `HITL`)
- `Blocked by`
- `Goals covered`
- `Acceptance criteria`

Ask the user to review the slice set and dependency shape before creating anything:

- Does granularity feel right?
- Are dependency relationships correct?
- Should any slices be merged or split?
- Are HITL markings correct?

### 3. Create the epic if needed

If no epic exists yet, create one first and record its ID. Link it with `--spec-id design:<slug>`.

### 4. Create the beads

Create blockers first so dependency links have real IDs.

Every bead created from the design doc should link back with `--spec-id design:<slug>`.

```bash
bd create "<Slice Title>" --parent <epic-id> --type task \
  --acceptance "Criterion 1; Criterion 2" \
  --priority <priority> \
  --spec-id design:<slug>
```

Do not copy initiative-level design prose into bead `--design`. For design-linked slices, the
design doc already owns the design story. Use bead notes only for slice-local execution facts.

Link dependencies separately - `bd dep add` reads "**<from> depends on <to>**", so the second
argument is the prerequisite:

```bash
bd dep add <blocked-id> <blocker-id> # <blocked> waits on <blocker>
```

Do **not** use `bd create --deps "blocks:<id>"` for this: `blocks:<id>` means "*this* issue blocks
`<id>`" - the reverse, which silently inverts the graph.

After linking, confirm with `bd ready`: only slices with no blockers should appear.

For HITL slices, set the human gate by adding the `human` label:

```bash
bd label add <bead-id> human # surfaced by `bd human list`
```

If the project has a public issue tracker, create a tracking issue for each slice with a
`needs-triage` label and link it via `--external-ref gh-<number>`.

### 5. Close

Summarize what was created: the epic ID, the number of task beads, and any items labeled `human`.
Recommend reviewing HITL items before marking them ready.

## Pitfalls

- **Do not skip the sign-off step.** The user may want to adjust slice boundaries and dependencies.
- **Do not create beads out of dependency order.** Blockers need real IDs before you can
  `bd dep add <blocked> <blocker>`.
- **Do not mark all slices AFK.** Be honest about what needs a human decision.
- **Do not include implementation detail in acceptance criteria.** Keep them outcome-focused and
  verifiable.
- **Do not use `--design` for design-linked initiative slices.** Use `--spec-id design:<slug>` and
  keep the living design in the design doc.
