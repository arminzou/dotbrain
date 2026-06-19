# Operating beads: the native model

The beads engine reference for `operate-execution`, loaded when `execution-engine: beads`. Covers
how to model, author, and resume work in beads' own fields, and why that beats inventing a label
vocabulary on top. This is the opinion layer; for the version-current command list and flags, run
`bd prime` — it is authoritative, so do not reproduce the full reference here.

The one rule everything below serves: **beads is a typed, prioritized dependency graph. Express
work in the native fields the graph already has; reach for labels only for a dimension the graph
has no field for.** Every time you re-encode a native concept as a label, you create a second
source of truth that drifts.

## Command quick reference

Run from the repo root or Brainspace; use `bd -C <repo-or-Brainspace> ...` from elsewhere. The
store lives in the Brainspace's `.beads/`. `bd prime` reloads the session protocol and the
current command set.

```bash
bd ready                                   # claimable work: open, no open blockers
bd list --status open                      # survey
bd show <id> --long                        # full item detail
bd create "Title" --type task --description "..."
bd create "Epic title" --type epic
bd create "Child" --parent <epic-id> --type task
bd dep add <blocked-id> <blocker-id>       # "<blocked> depends on <blocker>"
bd update <id> --claim                     # sets in_progress + ownership
bd close <id> --reason "..."
bd dolt pull   /   bd dolt push            # sync the shared store
```

## Choose `--type` deliberately

Native types: `bug | feature | task | epic | chore | decision` (aliases: `enhancement → feature`,
`adr → decision`). Type is structured metadata; never restate it as a `bug`/`enhancement` label.

- `bug` — something is broken against intended behavior.
- `feature` — new capability or enhancement (`enhancement` is an alias, not a separate kind).
- `task` — a unit of work that is neither a defect nor a new capability (the default).
- `chore` — maintenance with no behavior change (deps, renames, cleanup).
- `epic` — a parent that groups child issues; give children `--parent <epic-id>`.
- `decision` — a beads-native decision record. In dotbrain we do **not** use this: decisions live
  as ADRs in `.brain/adr/` (owned by `grill-decisions`). Beads tracks execution, not decisions.

## Dependencies: types and direction

Priority and dependencies answer different questions; do not conflate them.

- `--priority 0-4` (0 highest) orders work that is *already ready*. A ranking, not a gate.
- a dependency records a real relationship between issues; only `blocks` gates the ready queue.

**Direction:** `bd dep add <from> <to>` reads "from depends on to" — the *to* issue is the
prerequisite. `bd dep add api storage` means storage blocks api.

| Type | Meaning | Effect on `bd ready` |
|---|---|---|
| `blocks` | hard prerequisite: cannot start until it closes | withholds the blocked issue |
| `parent-child` | epic/subtask hierarchy (`--parent <epic-id>`) | structural; groups work |
| `discovered-from` | provenance: found while working on another issue | none; records history |
| `related` | soft context link | none; navigation only |

- Use `blocks` for genuine prerequisites only, never for preference or ordering; that is what
  priority is for. Over-blocking starves `bd ready`.
- Discovered work mid-task: create it with `--deps discovered-from:<current-id>` and keep going.
  The provenance survives after both close; `bd dep tree <id> --reverse` shows the discovery chain.
- Never encode a dependency as prose ("blocked by task 02"); the graph cannot act on prose.

## Readiness is computed, never labeled

`bd ready` is the authoritative view of claimable work: it returns open issues with no open
blockers. It is derived from the graph every time you run it, so it cannot go stale.

Do **not** create a `ready` / `ready-for-agent` label. A static readiness flag can only agree with
the computed graph by luck and disagree with it by neglect. If something should be claimable, make
sure its blockers are closed; if it should not, add the dependency. Let `bd ready` answer.

## Status lifecycle

`open → in_progress → closed`, with `blocked` and `deferred` as side states.

- Claim before working: `bd update <id> --claim` (sets `in_progress` and ownership).
- `blocked` is *derived from dependencies*. Do not hand-set a blocked status or a blocked label;
  add the dependency and let the engine compute it.
- `deferred` (`bd defer <id> --until=...`) parks work that is real but not now. Prefer this over a
  `later`/`backlog` label.
- Resolve with a reason, not a label: `bd close <id> --reason="wontfix: ..."`. The close reason is
  the durable record; a live `wontfix` label on a closed issue is redundant.

## Human gate: the autonomy boundary

Flag `bd human <id>` when an issue needs a person's decision before an agent can proceed. This
is the **gate**: the agent picks up unflagged items autonomously and only stops for flagged ones.

- Flag it when the item has: scope ambiguity, design trade-offs, cross-cutting impact, or anything
  you want to inspect before work starts.
- Leave it unflagged for small, routine, well-scoped work the agent can finish without input.
- Queryable: `bd human list` shows all gated items. The agent checks this before each new item.

## Authoring issues: design vs acceptance

Ask before creating when scope is fuzzy: knowledge work, unclear boundaries, multiple valid
approaches. Create directly when scope is clear: a bug found mid-implementation, an obvious
follow-up, scoped tech debt, a discovered blocker.

Keep two fields distinct, because they have different lifetimes:

- **`--design` is HOW**: approach, architecture, trade-offs. It may change during implementation.
- **`--acceptance` is WHAT**: the outcomes that define done. It should stay stable across sessions.

Acceptance criteria must be **outcome-focused and verifiable**, not steps. Self-test: if you
rebuilt the solution a different way, would the criteria still hold? If not, they are design notes
masquerading as criteria.

- Good acceptance: "Bold and italic render in the output; files over 50KB process without timeout."
- Wrong (design as criteria): "Use the two-phase batchUpdate approach."

## Resumable notes: survive compaction

beads exists so work survives session boundaries and context compaction; the notes field is how.

- Write notes as **current state, not a cumulative log**: where the work stands now and what is
  next, so the next session (or the post-compaction you) can resume cold.
- Always include: what is done, what is next, any open question.
- For multi-session technical work, enhance with tested code, real sample outputs, and the target
  format (show, do not describe). Skip this weight for simple tasks.
- On close, document the **actual outcome**, not the original hypothesis: if the design changed,
  say what really happened in the close reason or notes.
- Recover after compaction with `bd list --status in_progress`, then `bd show <id> --long`;
  `bd prime` reloads the session protocol.

## Labels: the one place they earn their keep

Beads has a real, well-filtered label primitive (`--label` AND, `--label-any` OR,
`--label-pattern 'area-*'`, `--label-regex`, `--exclude-label`). Spend it only on **orthogonal
facets the graph has no native field for**:

- component / area: `area:cli`, `area:skills`, `area:brain`, `area:docs`
- cross-cutting qualities: `tech-debt`, `security`, `breaking`

Rules:

- **Never** label something that a native field already records: not type (`bug`/`enhancement`),
  not readiness, not status, not resolution. That is the drift trap this whole document exists to
  prevent.
- Keep the facet vocabulary small and disjoint; avoid label proliferation.
- A project records its adopted facets (and, when intake is connected, the GitHub mapping below) in
  `.brain/agents/labels.md`. An absent file means no project labels: pure native fields.

## Promoting a public issue inward

When `triage-public` hands a GitHub issue to private execution, you *translate* its labels into
native fields; you do not copy the labels onto the bead. GitHub issues are flat, so GitHub fakes
type/readiness/resolution with labels; beads has real fields for each.

| GitHub label | What it means | Native beads action |
|---|---|---|
| `bug` | defect | `--type bug` |
| `enhancement` | new capability | `--type feature` |
| `needs-triage` | not yet refined | leave as a GitHub state; create the bead only once accepted |
| `needs-info` | waiting on reporter | keep on GitHub; do not create private work yet |
| `ready-for-agent` | accepted for agent work | create the bead; `bd ready` governs readiness thereafter |
| `ready-for-human` | needs a person | `bd human <id>` after creating, or keep on GitHub |
| `wontfix` | rejected | do not create a bead; resolve on GitHub |

Always link the layers with `--external-ref gh-<number>` so the bead points back at its public
origin. Keep status independent across the two; a PR's `Closes #N` closes the GitHub issue only,
and the bead still needs `bd close`.

## Anti-patterns

- **Do not** mirror beads status into markdown docs, ROADMAPs, or TodoWrite/task lists. beads is
  the source of truth; `bd ready` / `bd list` is the view.
- **Do not** re-encode `--type` as a `bug`/`enhancement` label.
- **Do not** create readiness, blocked, or status labels; those are computed or set natively.
- **Do not** hand-set `blocked`; add a dependency.
- **Do not** record decisions as `--type decision` beads here; dotbrain keeps decisions as ADRs in
  `.brain/adr/` (owned by `grill-decisions`).
- **Do not** carry a triage-label vocabulary in private beads; triage labels are a GitHub-surface
  concern that `triage-public` maps inward.
