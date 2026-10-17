# Writing within dotbrain

Dotbrain gives agent-consumed writing three visibility surfaces. The writing principles in
[`SKILL.md`](../SKILL.md) apply to all three; placement and authority differ.

| Surface | Typical documents | Constraint |
|---|---|---|
| Public project repository | `AGENTS.md`, `CLAUDE.md`, README, architecture, contributor and referenced project docs | Must remain useful without access to the private Brain and contain no private Brain material |
| Private project Brain | `AGENTS.md`, `DOTBRAIN.md`, `CONTEXT.md`, ADRs, designs, `RETRO.md`, and `.brain/docs/` | Private rules/preferences, shared operations, vocabulary, decisions, findings, and design history |
| User data root | Skills under `$DOTBRAIN_HOME/skills/` and their references | Follow the nearest authoring policy; linking and invocation remain explicit operator choices |

Public and private documents may point across the boundary only through the public-safe convention
defined by the project's context workflow. Keep the private rationale in the Brain and express any
publicly necessary reasoning without leaking private paths, identifiers, or operational state.

Public `AGENTS.md` routes making or reviewing changes to tracked root `RULES.md` and task-specific
references. Shared `DOTBRAIN.md` owns private retrieval; the lead or sole agent searches the
retrospective for relevant findings and passes them through assignments. Private `.brain/AGENTS.md`
holds a small set of personal preferences and private project rules, with `CLAUDE.md` as its alias.
Keep repository requirements in public `RULES.md` and preserve private preferences privately.

Use dotbrain's specialized workflows when the task changes structure or lifecycle:

- `curate-project-context` audits and repairs context placement, reachability, drift, and canonical
  `AGENTS.md`/`CLAUDE.md` relationships.
- `to-design`, `iterate-design`, and `close-design` own the design lifecycle.
- `grill-decisions` resolves contested terminology and durable decisions; other active workflows
  may write already-settled vocabulary or promote their own residue using the established formats.

Those workflows determine what belongs in a document and when it changes. The parent skill
determines how the resulting writing retrieves cleanly, directs action, and remains maintainable.

## Section contract for dotbrain skills

A skill's sections follow from its shape, so a reader can tell from an absent section that the
skill does not need it rather than that someone forgot. Pick the shape first.

| Shape | Carries |
|---|---|
| **Linear procedure** — ordered steps, run once | A bail-out section *above* the steps · `### N.` step headings · a `Completion:` line closing every non-terminal step · a named terminal step |
| **Loop** — steps that repeat until a condition | A bail-out section · a numbered protocol · **one exit condition** in place of per-step criteria |
| **Reference** — rules consulted on demand | Title and body. No criteria, no terminal step |
| **Driver** — routes to a CLI or external tool | A branch selector · a symptom-to-command table · a verification list |

Three rules decide the variable parts:

- **The bail-out goes above the process, not inside it.** A condition written as step 1 is only
  reached once the skill is loaded and the run has begun; above the steps it is read while the
  agent can still choose something else. Name it `## Stop before you start`. Two shapes need none:
  a read-only diagnostic, where running costs nothing to undo, and a user-invoked skill, where the
  human already made the call.
- **Per-step criteria are for linear procedures only.** A step that repeats cannot be "done", so a
  loop states the condition that ends it instead — an empty ready frontier, a `FINAL` verdict, a
  retry cap. A loop with no per-step criteria is correct, not incomplete.
- **The terminal step is named for what actually happens.** `Close` when the skill ends the work,
  `Hand off` when it routes onward to another skill, `Report` when it presents findings for a human
  to authorize. A skill whose last step already lands the outcome in its own criterion needs no
  separate terminal step.
