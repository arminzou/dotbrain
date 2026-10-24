# Dotbrain skills

Dotbrain's skills cover the work around shipping software: build and maintain project context,
turn an idea into a design and tasks, implement, review, and close out the result. Each skill has a
bounded job and hands off what it learned. The Brain holds shared vocabulary and decisions, the
active design records current intent, and Beads tracks private execution.

## Core workflow

- **Wire:** [`wire-brain`](wire-brain/SKILL.md) provisions or repairs a project's Brainspace wiring.
- **Build context:** [`find-unknowns`](find-unknowns/SKILL.md) surfaces blind spots;
  [`grill-decisions`](grill-decisions/SKILL.md) settles shared terms and durable choices;
  [`curate-project-context`](curate-project-context/SKILL.md) keeps that context coherent as it grows.
- **Design and decompose:** [`to-design`](to-design/SKILL.md) writes the living design and opens an epic;
  [`to-issues`](to-issues/SKILL.md) cuts it into workable tasks with dependencies.
- **Implement and learn:** [`manage-work-graph`](manage-work-graph/SKILL.md) keeps the work graph and
  its ready frontier; [`run-execution`](run-execution/SKILL.md) carries out an item or a
  finite batch. Discoveries feed back into the active design or work graph before the next work item.
  Hand a design off to [`iterate-design`](iterate-design/SKILL.md), by name or in words, for a bounded handoff loop.
- **Review:** [`review-gate`](review-gate/SKILL.md) records findings and verification evidence; the lead
  closes accepted reviews, and PR approval and merge stay human-owned.
- **Close out:** ask for [`close-design`](close-design/SKILL.md), by name or in words, to record what was verified,
  promote lasting knowledge, and freeze the design as shipped, abandoned, or superseded.
- **Supporting writing guidance:** [`write-agent-docs`](write-agent-docs/SKILL.md) guides public docs,
  private Brain material, and agent instructions. It remains model-invocable.

The person owns success criteria and approves changes to them. The agent stops when a criterion
needs to change rather than quietly redefining done.

## Optional skills invoked by name

These skills stay shipped. Use `/dotbrain:<name>` in Claude Code or `$<name>` in Codex.
`dotbrain` and `triage-public` also start from a request in words; the others run only by name.

- **Learn:** [`teach-me`](teach-me/SKILL.md) teaches the project from its Brain across sessions.
- **Triage:** [`triage-public`](triage-public/SKILL.md) brings accepted public issues into private execution.
- **Brain site:** [`brain-site`](brain-site/SKILL.md) sets up, builds, and previews the private site.
- **Architecture:** [`review-architecture`](review-architecture/SKILL.md) looks for architectural deepening opportunities.
- **Convention:** [`dotbrain`](dotbrain/SKILL.md) provides the operating convention. The session-start
  hook injects it automatically; where that hook does not run, ask for it or invoke it by name.
- **Retrospective:** [`run-retro`](run-retro/SKILL.md) reviews changed evidence in a separate manual or
  externally invoked pass, retaining private findings, successful practices, and source progress.
  In repository scope it offers once to create `RULES.md` when no rules or standards file
  exists; contributor scope never creates one. It may prepare a public `RULES.md` change and
  reads PR/merge state read-only to reconcile
  acceptance. By default it suggests an existing public destination for the user's decision,
  along with the strongest mechanical enforcement for the rule, which it never builds itself.
  Public delivery needs proposal-specific authorization or enabled project auto-delivery with
  a configured destination; run-retro owns its PR process. Approval and merge remain human-owned.

See the [full skill catalog](../../docs/skills.md) for the other skills and
[getting started](../../docs/getting-started.md) for installation.
