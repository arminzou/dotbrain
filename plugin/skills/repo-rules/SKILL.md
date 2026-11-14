---
name: repo-rules
description: Initializes and reconciles repository requirements in RULES.md and agent routing in AGENTS.md, and assesses enforcement gaps. Use when asked to establish repository rules, maintain adopted requirements, or assess or hand off their enforcement.
---

# Repository rules

Maintain adopted public repository requirements and their agent routing.
[assets/RULES.md](assets/RULES.md) is Dotbrain's standalone engineering baseline.
It needs no private library or engineering workflow to be read or adapted.
Changes to the packaged baseline follow normal product review; repository-specific
requirements belong in the target repository.

## Select the operation

| Request | Operation |
| --- | --- |
| Initialize repository rules or reconcile them with the baseline. | Initialize or reconcile rules and routing below. Explicit initialization authorizes applicable baseline and routing edits. |
| Maintain an adopted requirement. | Reconcile the scoped requirement with existing guidance; preserve unrelated content. |
| Assess coverage or enforcement. | Assess below, without editing files. Missing rules remain proposals. |
| Implement enforcement of a requirement. | Assess the scoped gap, then hand implementation to the selected engineering workflow. |

A bare invocation assesses the repository. Create or reconcile baseline rules only
when requested; invocation alone does not adopt proposed requirements. Apply user
and repository authority to every edit. Conflicting requirements need resolution;
continue independent authorized work without silently choosing a side.

## Initialize or reconcile

1. Identify the repository and read applicable instructions, existing requirements,
   specialist guides, validation configuration, and CI. Inspect representative code
   for actual conventions and dependency boundaries. Find the authoritative public
   destination before editing; retain an existing standards or contributor guide
   rather than introducing competing requirements.
2. For requested initialization or baseline reconciliation, read
   [assets/RULES.md](assets/RULES.md). Adapt application guidance to inspected
   conventions, paths, and tools while preserving each rule's intent. Keep
   applicable rules even when they need human review. Invent no architecture,
   commands, platforms, or adoption of repository-specific constraints.
3. Reconcile by meaning with the current content, rereading before saving if
   another writer may have changed it. Preserve local amendments, existing
   requirements, exceptions, rationale, and unrelated guidance. Account for each
   baseline rule as included, already covered, inapplicable with a reason, or
   conflicting. Improve the existing application guidance when it already covers
   the decision; add a rule only for a distinct adopted requirement. Keep proposals
   and unresolved conflicts out of the adopted requirements.
4. Add or reuse a concise root `AGENTS.md` pointer directing agents making or
   reviewing changes to read `RULES.md`, or the repository's existing authoritative
   requirements destination. Create minimal routing if needed. Preserve aliases
   and unrelated guidance; do not copy rules or README onboarding into routing.
5. Check coverage, local links, and named commands against actual configuration.
   Review the complete diff for lost requirements or private context. Confirm that
   repeating reconciliation would add no duplicate rules or routing and would
   preserve local amendments.

Completion: the requested requirements and routing are reconciled, every scoped
baseline rule is accounted for, and conflicts remain explicitly unresolved.

## Rule format and authority

A rule states a durable requirement, its scope, and how contributors or reviewers
recognize compliance. A broad principle does not establish a concrete dependency
boundary or command; discover and name the accepted constraint. Personal
preferences and supported findings remain proposals until adopted. A recurring
failure alone does not authorize a new requirement or permanent workaround.

Use work-area groups and `Rule` / `How to apply` tables for a new `RULES.md`.
Preserve an established requirements format when reconciling. Write each rule as
a short plain sentence without bold formatting. Keep each row self-contained:
put scope, application, observable checks, necessary rationale, exceptions, and
links in `How to apply`; escape literal pipes in cells.

Keep each requirement in one authoritative location. Link specialist guides and
configuration for details instead of duplicating them, and check overlapping
guidance agrees. Derive commit conventions from accepted guidance and history;
do not impose a generic convention. Public wording must stand alone in an ordinary
clone. Keep private evidence, personal paths, finding identifiers, and incident
history private when deriving an adopted public requirement.

## Assess enforcement

Read the scoped requirements, affected code, existing checks, and supplied failure
examples. Compare coverage with the baseline; missing or conflicting requirements
are proposals, not newly adopted policy. If no requirements file exists, recommend
initialization rather than performing it.

For each scoped adopted rule, locate existing enforcement and identify the concrete
gap. Prefer an existing type or API boundary that prevents invalid choices, then
an existing static or architectural check, or a targeted behavioral test. Use a
mechanism that expresses the requirement; retain judgment-based decisions in
review guidance. Distinguish missing policy, missing enforcement, and a failure
to discover or follow guidance that already covers the decision.

Report the rule, adoption source, existing check location or command, observed
evidence, gap, smallest proposed change, and remaining limitation. Separate
inspection from demonstrated enforcement. Static evidence establishes static
constraints; runtime, integration, browser, and visual claims require evidence at
those levels. Local checks and observed CI runs are separate claims.

## Hand off enforcement

For requested enforcement, provide the selected engineering workflow with the
adopted rule and its authority, affected boundary and existing checks, proposed
mechanism, and verification needed to reject a representative violation and
accept valid behavior. Reuse an assessment only while it matches the repository.
Unadopted requirements and unresolved conflicts remain explicit decisions for
the appropriate authority before enforcement.

The selected workflow owns implementation in code, types, tests, lint, hooks, or
CI, along with verification and delivery procedures under user and repository
authority. This core operation does not implement those changes or prescribe
branching, delegation, review, pushes, PRs, or release steps. If no workflow is
selected, return the concrete assessment and handoff without claiming execution.

## Report

Identify changed files, baseline coverage and omissions, unresolved conflicts,
checks actually performed, and remaining proposals. Distinguish written
requirements from demonstrated enforcement and work handed to the workflow.
