---
name: to-issues
description: Break a design doc into independently-workable bead tasks under an epic. Decomposes the plan into vertical-slice issues with acceptance criteria and dependencies. Use when a design doc is ready and you want to create the execution graph.
---

# To Issues

Take a design doc and decompose it into bead tasks under the epic. Each task is a thin, vertical
slice that cuts through all integration layers - a demoable unit of work. The design doc remains
the initiative-level design authority; beads carry execution.

## Boundaries

- **vs `to-design`**: that authors the design doc and opens the epic; this fills the epic with
  slices. Run it once per design doc, after the design is settled enough to cut up.
- **vs `operate-execution`**: both create beads, at different scales. That takes work in one item at
  a time as it arrives and runs the ready frontier; this is a single bulk decomposition of a whole
  initiative. Its `references/work-intake.md` owns the call between the two.
- **vs `iterate-design`**: that executes slices; this creates them. Decomposition ends where
  implementation begins.
- **vs `triage-public`**: that promotes existing public issues inward with provenance. This works
  from a private design outward into private beads, and never creates public tracking issues.

Pipeline position: `to-design` (capture), then `to-issues` (decompose), then `operate-execution`
(build).

## Process

### 1. Find the design doc

If the user passes a design doc path or name, use that. Otherwise, find the latest design doc in
`.brain/designs/`:

```bash
ls -t .brain/designs/*.md | head -1
```

Read the full design doc, especially `Goals`, `Design`, `Known Unknowns`,
`Implementation Notes`, `Deviations`, and `Non-goals`.

Completion: you can name the design doc slug and state its goals and non-goals without re-reading.

### 2. Draft vertical slices

Decompose the goals and implementation notes into vertical slices. Each slice should deliver a
narrow but complete path through every relevant layer. A completed slice should be demoable or
otherwise verifiable on its own.

Sequence the slices by volatility: within their dependency constraints, put the ones that resolve the
most volatile, highest-blast-radius decisions — data models, type interfaces, migration shape — first.
Validating a risky assumption in the first slice is far cheaper than discovering it wrong in the fifth.

Word each slice `Title` to echo the corresponding `Design` subsection heading or a
distinctive phrase from it. This lets a later reader match a bead straight back to its exact
design-doc section by title alone, without re-reading the whole document.

For each slice, show:

- `Title`
- `Gate` (`autonomous` or `human-gated`)
- `Blocked by`
- `Goals covered`
- `Acceptance criteria`

Mark a slice human-gated when it needs a person's decision, and be honest about which do: a set
where everything is autonomous is usually a set that has not been read carefully. Keep acceptance
criteria outcome-focused and verifiable, stating what is true when the slice is done rather than how
it was implemented.

Ask the user to review the slice set and dependency shape before creating anything:

- Does granularity feel right?
- Are dependency relationships correct?
- Should any slices be merged or split?
- Are the human-gated markings correct?

Completion: every goal in the design doc is covered by at least one slice, every slice names the
goals it covers, and the user has signed off on the set.

### 3. Create the epic if needed

If no epic exists yet, create one first and record its ID. Link it with `--spec-id design:<slug>`.

Completion: an epic ID exists and its `--spec-id` matches the design doc slug.

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

For human-gated slices, set the gate by adding the `human` label:

```bash
bd label add <bead-id> human # surfaced by `bd human list`
```

Keep every slice in the private execution graph. A configured public tracker is an intake and
contributor-collaboration surface, not a second execution graph; decomposition never creates public
tracking issues.

Completion: every reviewed slice exists as a bead carrying `--spec-id design:<slug>`, `bd ready`
lists exactly the unblocked ones, and every human-gated slice carries the `human` label.

### 5. Close

Summarize what was created: the epic ID, the number of task beads, and any items labeled `human`.
Recommend reviewing the human-gated items before marking them ready.

## Hard guardrail

**Do not use `--design` for design-linked initiative slices.** Use `--spec-id design:<slug>` and
keep the living design in the design doc. The field looks like the right home and silently splits
the design across two places.
