# Skills

The dotbrain plugin delivers its Brain-coupled skills: the operating manual for a wired project.
They cover wiring, planning, execution, triage, and Brain maintenance. Several are inspired by and adapted
from [mattpocock/skills](https://github.com/mattpocock/skills).

[The workflow](workflow.md) shows how they fit together.

Skill linking is operator-managed:

- global skills are selected in `~/dotbrain/skills/skills.yaml`
- per-project skills are selected in `brainspaces/<name>/.brain/project.yaml`

## Select and reconcile skills

Codex project skills are linked into `<checkout>/.agents/skills/`. Its configuration and
subagents remain under `.codex/`; global skills still use `~/.codex/skills/` and configured
profiles. Claude Code and the other runtimes keep their existing destinations.

`wire`, `refresh`, and `skills link` migrate legacy `.codex/skills/` links whose targets establish
Dotbrain ownership. A selected legacy link is removed only after its replacement is delivered;
stale owned links are pruned. Foreign or ambiguous files, directories, and links are preserved
and reported. Destination collisions keep the legacy link until you resolve the conflict and
rerun reconciliation. Each managed resource is ignored individually, and `unwire` removes owned
links from both locations. These delivery checks establish filesystem state; native runtime
discovery and invocation need separate verification.

Both scopes accept an individual skill or a bundle directory:

```yaml
# ~/dotbrain/brainspaces/my-app/.brain/project.yaml
skills:
  - my-collection/specific-skill
  - another-collection
```

```yaml
# ~/dotbrain/skills/skills.yaml
version: 1
profiles:
  claude-code: [~/.claude-work]
global_extra:
  - another-collection
```

Global linking uses each runtime's default home. For Claude Code and Codex, `profiles` adds
extra homes, each receiving skills in `<home>/skills`; missing homes are skipped. Use runtime
homes rather than folders inside project checkouts. See [configuration](configuration.md#skills-skills-yaml)
for migration from legacy `targets`.

A directory containing `SKILL.md` selects itself, even when it has descendant skills. Otherwise
dotbrain discovers descendant `SKILL.md` directories recursively, excluding `node_modules`.
Overlapping selections of the same source are deduplicated. Different sources mapping to the
same destination name, including case collisions on a case-insensitive filesystem, fail before
destination changes. Missing paths, non-directories, and empty bundles fail actionably.

```bash
dotbrain skills list                         # discover sources
dotbrain skills link                         # current wired checkout
dotbrain skills link --project my-app         # registered checkout
dotbrain skills link --scope global           # explicit global homes
dotbrain skills link --runtime codex           # declared Codex workspace only
```

Adding or removing skills from a selected bundle takes effect on the next reconciliation; the
declaration stays unchanged. Removed owned links are pruned, while foreign entries are preserved.
`projects show`, catalogs, and doctor use the same expanded selection.

## Core workflow

Wire, decide, design, decompose, execute, review, close, and curate project context.
`write-agent-docs` supports the workflow with writing guidance and remains model-invocable.

### Setup

- **`wire-brain`** — provision or repair Brainspace wiring between a repo and its private Brain,
  including restoring a linked worktree's `.brain` and `.beads`. Installs the `dotbrain` CLI on
  first use if it is missing.

### Planning

- **`to-design`** — formalize a multi-step initiative into a living active design doc, save it to
  the Brain, and create an epic bead. Use when the work needs explicit design shape or a place to
  track unknowns before decomposition.
- **`to-issues`** — decompose a design doc into independently-workable bead tasks with acceptance
  criteria and dependencies, linking each bead back with `--spec-id design:<slug>`.
- **`grill-decisions`** — stress-test a plan against project vocabulary and decisions, then write
  durable results into `CONTEXT.md` and `adr/`.
- **`find-unknowns`** — surface blind spots and tacit assumptions in unfamiliar territory before
  committing to a design.
- **`close-design`** — drive a design doc to a terminal state: check actual PR merge
  evidence for shipment, record evidence, promote residue to
  `adr/` and `CONTEXT.md`, close the epic.

### Execution

- **`manage-work-graph`** — file, inspect, claim, split, update, and close work items in the private
  work graph
- **`run-execution`** — carry out one work item or a fixed batch: dispatch workers, have each
  change reviewed independently, integrate, check, repair within limits, and escalate or recover
- **`iterate-design`** — run an active design doc through the agent's native loop mode: plan,
  implement, verify, reflect, deliver through a draft pull request that becomes ready for your
  review, and stop on success or blocked

### Review and curate

- **`review-gate`** — run a durable review gate (code, simplification, or readiness) and record the
  outcome on the issue; the lead closes accepted reviews before PR merge after required exact-revision
  evidence and finding dispositions. Human PR approval, merge and release remain separate
- **`curate-project-context`** — find and repair stale, duplicated, misplaced, unreachable, or
  leaking context across the public project and private Brain
- **`write-agent-docs`** — writing discipline for public project docs, private Brain material,
  user-owned skills, and guidance agents reach through pointers

## Optional skills invoked by name

These skills stay shipped. In Claude Code, use `/dotbrain:<name>`; in Codex, use `$<name>`.
`dotbrain` and `triage-public` also start when you ask for them in words; the others run only by name.

- **`dotbrain`** — the operating convention itself. The session-start hook injects it
  automatically; in runtimes where the hook does not run, ask for it or invoke it by name.
- **`run-retro`** — keeps agents from repeating mistakes, while you can see and steer the loop.
  It has two modes. **Curate** (manually, or from an agent-host schedule you set up) reads work
  and review records changed since its curation cutoff (rejected candidates, `CHANGES` verdicts,
  failed checks, your corrections, informative successes), not commits. It merges and retires
  findings in private `RETRO.md`, dedupes them against `RULES.md`, tests, skill text, and
  structural fixes, and turns the retro candidates leads record on their work records at
  completion into findings, recovering ones they missed. It is the notebook's only writer, so
  leads on different designs or machines never race on it. For a finding nothing
  protects yet, it suggests the strongest intervention that fits (structure, type, check or hook,
  test, then rule text). It never builds that check itself; building one is separate work you
  approve. **Audit** runs only when you ask, over a scope you choose, and is read-only: it judges
  from later assignments and review verdicts whether supplied findings changed behavior, and
  recommends keep, revise, or stop.
  A run with nothing worth your attention is silent. Otherwise its short report puts decisions
  first, each with a recommended option; an unanswered decision stays pending and authorizes
  nothing. A manual run asks you about pending decisions through the runtime's question dialog
  where one exists. Notebook writes use a compare-and-swap save, so a failed or overlapping run
  loses nothing and the next run repeats its work.
  Public auto-delivery is off by default: suggestions stay private for your decision. Set
  `retro.promotion.auto-deliver: true` and an existing repo-relative `destinations` array in
  private project configuration to authorize unattended commit/push/PR delivery. Otherwise
  authorize individual proposals. It reads PR/merge state read-only to reconcile acceptance;
  approval and merge remain human-owned. An adopted `RULES.md` uses `Rule` / `What to check`
  tables; other guides retain their conventions. Rule proposals have run-retro's own PR process
  and body, independent of the `pr` skill used for ordinary changes.
  First use reads existing root guidance and referenced standards, records a curation cutoff,
  and stops without reviewing history. In repository scope with no rules or standards file, it
  offers once, on the first pass until answered, to create `RULES.md` from requirements existing
  guidance already states and delivers it as a PR; contributor scope never creates a file in the
  repo. Curation stays within explicitly selected contribution branches/PRs or a
  maintainer-selected integration branch; missing scope is reported instead of assumed.
- **`triage-public`** — classify public tracker items and promote ready work into private execution
- **`review-architecture`** — review the codebase for architectural deepening opportunities

### Brain Site

- **`brain-site`** — explicitly invoke to set up, maintain, build, or preview a Brain's private
  site with `dotbrain site`, including sidebar, theme, and rendering checks

### Learning

See [Learning your project](learning.md) for learning paths, parked concepts, and session continuity.

- **`teach-me`** — teach the operator their project from its Brain over many sessions: explain in
  conversation, walk a learning path tracked as a `learn:` bead, record what was demonstrated, and
  capture approved lessons into `.brain/learning/`

## Subagents

Alongside the skills, dotbrain ships Brain-aware subagents: `worker`, `reviewer`,
`verifier`, and `researcher`. See
[Session context](session-context.md#subagents).

Global extras selected in `agents/agents.yaml` use the same default homes and `skills/skills.yaml`
`profiles:`, delivered into `<home>/agents` for Claude Code and Codex. See
[configuration](configuration.md#agents-agents-yaml) for legacy `targets:` migration.

## Installing Them

The skills arrive with the plugin, installed once per agent runtime rather than per repo. See
[getting-started.md](getting-started.md) for the install commands. Because the plugin installs at
user scope, its skills are available in every session, including repos that are not wired yet.

Hermes gets the skills from a plugin copy that `dotbrain bootstrap --runtime hermes`
places in the Hermes home, and a project's selected skills from `.hermes/skills/` in a trusted
checkout. Hermes lists manual-only skills, but the model cannot load them; invoke them yourself.
See [Hermes](getting-started.md#hermes).

OpenCode gets the skills from the packaged copy that
`dotbrain bootstrap --runtime opencode` places in the OpenCode config directory, and a project's
selected skills from `.opencode/skills/` in the checkout. Skills keep their own names, without the
`dotbrain:` prefix. Manual-only skills are not enforced: OpenCode lists them and the model can
invoke them. See [OpenCode](getting-started.md#opencode).

Pi gets the skills from the extension that
`dotbrain bootstrap --runtime pi` places in the Pi agent directory, and a project's selected skills
from `.pi/skills/` in a trusted checkout. Manual-only skills are hidden from the model; invoke them
with `/skill:<name>`. See [Pi](getting-started.md#pi).

Cursor gets the packaged skills from your dotbrain Claude Code plugin, or from a copy dotbrain
keeps when that plugin is missing, disabled, or outdated. It also reads `.claude/skills`,
`.codex/skills`, and `.agents/skills`, so dotbrain links into `.cursor/skills/` only the skills
Cursor would not otherwise find. Manual-only skills run only as `/<name>`. See
[Cursor](getting-started.md#cursor).

Edit bundled skills directly in [`plugin/skills/`](https://github.com/arminzou/dotbrain/tree/main/plugin/skills).
