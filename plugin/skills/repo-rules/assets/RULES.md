# Repository rules

Apply the rules relevant to your change.

## Code conventions and structure

| Rule | How to apply |
| --- | --- |
| Follow established formatting, naming, and language conventions. | Prefer explicit configuration and accepted guidance; use nearby code where they leave a choice open. Run configured formatters and linters where available. Correct demonstrated defects within scope rather than copying them for consistency. |
| Respect established boundaries between components. | Review affected responsibilities and dependencies against the existing design; run available boundary checks. Correct boundary defects within scope without introducing unnecessary layers or an unrelated redesign. |
| Reuse established patterns and add complexity only for a concrete benefit in the current change. | Extract helpers for reuse, complex boundaries, or clearer callers; keep simple single-use expressions inline. Correct defective patterns within scope. Avoid speculative hardening while retaining required security, failure handling, and data protections. |
| Make code express its intent; reserve comments for information the code cannot convey. | Prefer clear names and structure over comments that narrate behavior or explain confusing code. Remove redundant and stale comments and commented-out code. Preserve required legal notices, public API contracts, and verified external constraints or rationale. Keep refactoring within scope. |
| Fix the underlying cause and remove recurring failure paths where practical. | Trace the failure before changing code. Prefer correcting the owning logic, simplifying the design, or making invalid states impossible over adding workarounds. Keep changes within scope; explain necessary workarounds and their limits. |
| Complete the requested change and preserve unrelated work. | Review affected callers, configuration, tests, and the full diff for missing updates. Update or remove affected documentation, examples, comments, and agent guidance so they describe the resulting behavior and no longer prescribe obsolete workarounds. Preserve unrelated edits and avoid unrelated cleanup. |

## Input, security, and failure handling

| Rule | How to apply |
| --- | --- |
| Validate untrusted input at its owning boundary and rely on those guarantees internally. | Verify boundary validation and invalid-input cases before relying on its guarantees downstream. Avoid repeating checks for guarantees the boundary actually establishes. |
| Preserve required security checks and protections against data loss. | Review authorization, persistence, and destructive actions; exercise relevant negative or integration cases to confirm protections still work after the change. |
| Preserve useful failure information and handle errors at the responsible layer. | Propagate errors with useful context; recover or report at the layer that owns that responsibility. Avoid catches that obscure the cause, and exercise failure paths to confirm failures cannot silently appear successful. |

## Verification

| Rule | How to apply |
| --- | --- |
| Encode requirements in automated checks when violations can be detected reliably. | Use existing types, API boundaries, linters, static analysis, or tests. Verify that the check rejects a representative violation and accepts valid cases. Make failures explain the violated requirement and expected correction. Keep judgment-based decisions in written guidance. |
| Verify the change with evidence appropriate to its behavior. | Run applicable syntax, build, type, and behavioral checks. Exercise integrations, runtime behavior, or interfaces when the claim depends on them, including visual checks when relevant. Distinguish pre-existing failures and state what remains unverified. |
| Prevent demonstrated regressions with targeted checks where practical. | Reproduce the failure; show the check rejects it and accepts valid behavior, or explain the limitation. Prefer extending existing tests or checks over introducing a framework or brittle wording assertions. |
| Preserve meaningful validation instead of weakening checks merely to pass. | Review tests, suppressions, exclusions, and CI changes. Investigate suppressions before adding or retaining them; fix the underlying issue when the check identifies a real defect. Update expectations when intended behavior changes; justify exceptions narrowly and preserve checks that detect incorrect behavior. |

## Source hygiene

| Rule | How to apply |
| --- | --- |
| Keep secrets and unintended local state out of tracked source. | Use established configuration and secret mechanisms. Inspect tracked changes and ignore rules; run configured secret checks where available. Distinguish private or generated local state from intentional platform configuration and sanitized examples. |
