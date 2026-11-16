# Rules maintenance

These examples show how common engineering requirements can be expressed and
maintained once a repository has adopted them. They are examples, not a default
policy or a coverage checklist. Use the repository's own authority, tools, scope,
and exceptions; keep unadopted suggestions separate from its requirements.

## Follow configured conventions

Suppose the contributor guide already requires the configured formatter and
linter, with exclusions for generated files. Clarify a vague rule such as
"keep formatting consistent" without choosing a new style:

| Rule | How to apply |
| --- | --- |
| Use the repository's configured formatting and lint rules. | Use the commands documented in the contributor guide and the checked-in tool configuration. Preserve the existing exclusions for generated files. Keep formatting changes within the requested scope. |

In a real repository, name the verified command and link its owning guide or
configuration. If the command changes, update that application guidance in place.
An exclusion remains until the repository changes it; a different preferred
formatter is a proposal, not a maintenance edit.

## Match verification to the change

Suppose accepted contribution guidance requires relevant checks before review,
and a separate release guide requires the full suite before release:

| Rule | How to apply |
| --- | --- |
| Verify changed behavior with the relevant existing checks. | Select checks that exercise the affected behavior, including integration or interface checks when the change crosses those boundaries. Report what ran, its result, and what remains unverified. Follow the release guide's full-suite gate when preparing a release. |

Name the repository's actual checks and link the release gate instead of copying
its procedure. When assessing a regression, identify which existing check should
reject it and whether that check actually does. A missing regression check is an
enforcement gap to hand off; it does not automatically justify a new framework or
running every check for every edit.

## Preserve security and data protections

Suppose the repository already requires authorization checks and preservation of
user-owned files during updates. Its security guide documents a separate admin
recovery path:

| Rule | How to apply |
| --- | --- |
| Preserve established authorization and data-loss protections. | For changes to access control, updates, or deletion, retain the existing permission and ownership checks and error handling. Verify the affected allowed and refused cases, including preservation of user-owned data. Keep admin recovery governed by the security guide. |

Link the existing checks, ownership boundary, and recovery guide after inspecting
them. Preserve the recovery exception rather than silently broadening or removing
it. A newly discovered destructive path should be reported with evidence and a
proposed guard; recording the finding alone adopts no new access policy.

Keep each requirement in its existing authoritative document. If these topics
already have rules, improve their application guidance instead of adding parallel
rows or creating another standards document. Preserve unrelated content and
existing agent routing. Distinguish finding a check from running it, and written
requirements from demonstrated enforcement.
