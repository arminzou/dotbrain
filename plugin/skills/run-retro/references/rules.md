# Public rule format

## What qualifies as a rule

A rule is a durable repository requirement with an applicable scope, required behavior,
and an observable check. It helps contributors make a decision and reviewers identify a
violation. Commit conventions count when adopted by the repository. Personal preferences
stay private unless the repository adopts them; generic advice such as "write clean code"
needs a concrete requirement before it can become a rule.

Use these areas as discovery prompts, not a template to fill:

| Area | Look for established requirements or supported findings about |
| --- | --- |
| Architecture | Dependency direction, module responsibilities, orchestration boundaries. |
| User data and filesystem changes | Preserving user content, checkout/data-root separation, destructive targets. |
| Managed resources | Ownership markers, reconciliation, foreign resources, symlinks. |
| Subprocesses | Injection seams, argument handling, explicit failure handling. |
| Verification | Test isolation, relevant checks, accurate results and omissions. |
| Compatibility | Supported platforms, paths, configuration and CLI contracts, migrations. |
| Public/private boundary | Public guidance that stands alone without leaking private evidence. |
| Documentation | Updating affected guidance and keeping examples consistent with behavior. |
| Commits and PRs | Message conventions, coherent scope, rationale and verification evidence. |

Create no category or rule merely to complete this list. During initialization, discover
existing guidance and record its links; do not copy standards into retrospective findings.
A `RULES.md` initialized outside this retrospective is an existing baseline, not a
template to reset. Read it and relevant linked guidance before proposing additions
or amendments, regardless of how it was initialized. Use the repository's adopted
rules; no external default collection or skill is required.
Within this skill, a new `RULES.md` comes only from the repository-scope [rules file offer](retro.md) and holds
only requirements existing guidance already states, never an invented comprehensive set. Existing adopted requirements need no
retrospective evidence. During later retrospectives, propose a specific addition or amendment only
from supported findings under [promotion](promotion.md); a proposal is not adoption.

## Distill repository-specific rules

For each supported finding, identify the repository condition that caused the problem,
the decision a future contributor must make differently, and how to recognize correct
application. Express the durable requirement using repository concepts. Keep incident
history and supporting evidence in the private finding.

Prefer correcting the owning design or adding reliable enforcement when appropriate.
Suggest those interventions through [promotion](promotion.md); do not implement them
from a retrospective. Written rules explain remaining decisions or constraints.

Compare the finding with accepted rules, relevant guides, existing enforcement, and
open proposals by meaning:

| Existing coverage | Action |
| --- | --- |
| Guidance or enforcement already addresses the concrete decision and its application. | Add no rule. Investigate discovery, compliance, or enforcement gaps instead. |
| A baseline rule applies but lacks necessary repository-specific detail. | Propose an amendment to its application guidance, using `How to apply` where that format is adopted. |
| The finding establishes a distinct repository-specific constraint. | Propose a new row in the relevant work area. |
| The finding conflicts with an adopted requirement or lacks sufficient evidence. | Keep it unresolved and surface the conflict or evidence gap. |

A broad principle is not sufficient coverage when it leaves the concrete decision open.
For example, "respect component boundaries" does not specify which dependencies are
forbidden. Discover the actual boundary, supported interface, and available check before
proposing details. Preserve baseline protections and unrelated repository requirements;
do not turn an incident-specific workaround into a permanent requirement without
establishing why the constraint remains necessary.

## Placement and detail

README describes the project and onboarding; AGENTS routes agents to relevant guidance;
public rules state what changes must satisfy. Specialist guides and configuration can remain
authoritative for detailed procedures or mechanically enforced conventions. Amend or link
those sources' guidance text instead of duplicating it; changes to enforcing configuration
follow [promotion](promotion.md) and are suggested, never made. Outside the repository-scope rules file offer,
a suitable existing contributing guide takes precedence over introducing a new file;
delivery requires the agreed destination and authority.

Use the repository's agreed public destination for repository requirements. Preserve an
existing standards or contributor guide's format; do not impose a new filename or table
structure on it. For a root `RULES.md` without an established format, group rules by work
area and use `Rule` / `How to apply` tables. Write each rule as a short sentence stating
the required behavior, without bold formatting. Keep each row self-contained: put scope,
application guidance, observable checks, necessary rationale, exceptions, and links in
the second column, rather than in supporting paragraphs. Escape literal pipes in cells.
Preserve existing unrelated guidance when adding rules.

A rule saying only "follow the commit convention" is insufficient unless its row links
to a concrete specification. For commit
rules, derive the subject structure, body expectations, and examples from the repository's
accepted guidance and history; do not impose a generic convention. Show actual checks only
when known, and clearly label placeholders or illustrative results.

## Example

```markdown
# Repository rules

Apply the rules relevant to your change.

## Managed content

| Rule | How to apply |
| --- | --- |
| Preserve user-owned content when updating managed instructions. | Change only the owned block; surrounding content stays byte-for-byte intact. |
```

This is a format example, not an automatically adopted rule. No private evidence, finding
IDs, recurrence counts, personal preferences, or promotion history belong in the public file.
Public rules must stand alone in an ordinary clone. A judged proposal is not policy
adoption. Several findings may support one rule, and several related
rules may share one PR. Other contributors' private notebooks are not shared evidence stores;
search accepted rules and open public proposals for overlap and conflict.

For repositories adopting `RULES.md`, keep public `AGENTS.md` as a routing document pointing
contributors to it. Do not
repeat README content or copy the rules into that routing document.
