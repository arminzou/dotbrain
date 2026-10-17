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
A new `RULES.md` comes only from the repository-scope [rules file offer](retro.md) and holds
only requirements existing guidance already states, never an invented comprehensive set. Existing adopted requirements need no recurrence
threshold. During later retrospectives, propose a specific addition or amendment only from
supported findings under [promotion](promotion.md); three dates justify a proposal, not adoption.

## Placement and detail

README describes the project and onboarding; AGENTS routes agents to relevant guidance;
public rules state what changes must satisfy. Specialist guides and configuration can remain
authoritative for detailed procedures or mechanically enforced conventions. Amend or link
those sources instead of duplicating them. Outside the repository-scope rules file offer,
a suitable existing contributing guide takes precedence over introducing a new file;
delivery requires the agreed destination and authority.

Use the repository's agreed public destination for repository requirements. Preserve an
existing standards or contributor guide's format; do not impose a new filename or table
structure on it. For an explicitly adopted root `RULES.md`, group rules by work area and use
`Rule` / `What to check` tables. State the applicable trigger and required behavior in the
rule; give an observable review check in the second column. Add a short rationale when the
constraint would otherwise be unclear. Keep rows short; put longer explanations below the
table. Escape literal pipes in cells. Preserve existing unrelated guidance when adding rules.

Tables are an index, not a limit on explanation. Add concise rationale, exceptions, and an
example below a row when needed to apply it consistently. A rule saying only "follow the
commit convention" is insufficient unless it links to a concrete specification. For commit
rules, derive the subject structure, body expectations, and examples from the repository's
accepted guidance and history; do not impose a generic convention. Show actual checks only
when known, and clearly label placeholders or illustrative results.

## Example

```markdown
# Repository rules

Apply the rules relevant to the change. Reviewers name the rule when reporting a violation.
AGENTS.md routes agents to guidance; README.md describes the project.

## Managed content

| Rule | What to check |
| --- | --- |
| Preserve user-owned content when updating managed instructions. | Change only the owned block; surrounding content stays byte-for-byte intact. |
```

This is a format example, not an automatically adopted rule. No private evidence, finding
IDs, recurrence counts, personal preferences, or promotion history belong in the public file.
Public rules must stand alone in an ordinary clone. Three supported evidence dates trigger
a proposal, not policy adoption. Several findings may support one rule, and several related
rules may share one PR. Other contributors' private notebooks are not shared evidence stores;
search accepted rules and open public proposals for overlap and conflict.

For repositories adopting `RULES.md`, keep public `AGENTS.md` as a routing document pointing
contributors to it. Do not
repeat README content or copy the rules into that routing document.
