# Public rule promotion

Use the saved capture contract, not retrospective run dates: `evidence_dates` is the unique
set of supported evidence days and `distinct_days` its size. Several observations on one day
count once; copied reviews and reruns add neither a day nor a rule. Resolve finding redirects
before looking up proposals. If the saved count and dates disagree, hold preparation and
report the capture gap; do not invent dates or silently repair capture here.

## Prepare one change

For each eligible finding with at least three supported days:

Promote only repository requirements. Personal preferences and private project rules stay in
`.brain/AGENTS.md`; recurring evidence alone does not make them public. Record that disposition
privately and skip the public proposal for such findings.

1. Identify the public repository and intended target branch explicitly from the existing
   delivery context. A delivery/integration branch is not the acceptance target. If the checkout
   or target cannot be identified, retain eligibility and record a hold. This procedure provides
   no alternate rules destination for a project without a repository.
   Record a verified target OID. Apply public edits only in a clean checkout or worktree based
   on that recorded target branch, with no unrelated feature work. Never edit `RULES.md` on
   an unrelated feature branch, even if clean; use the private patch fallback below instead.
2. Read root `RULES.md`, repository instructions, and applicable acceptance criteria. Compare
   rules by trigger and required behavior, not title or exact wording. Search both accepted
   rules and prepared changes, including proposals attached to other finding IDs. Reuse an
   equivalent rule that already says enough; amend its section when clarification is needed;
   append one section only when no equivalent exists. Several findings can share one proposal.
   A finding never overrides an established rule or acceptance criterion. Hold a conflicting
   proposal with the conflict and required human decision recorded privately; reaching three
   days does not settle that decision or authorize changing the criteria.
3. Derive fresh public wording with a trigger, required behavior, and enough rationale to stand
   alone in an ordinary clone. Express the reusable engineering constraint, not the incident.
   A reader must be able to follow the rule without the notebook or its sources. Use public
   repository concepts and paths only when needed to act on the rule.
4. Inspect the entire proposed public diff, including headings, links, comments, metadata,
   filenames, and any delivery text. Private paths, Bead IDs, design/review identifiers, private
   evidence, and notebook finding/proposal IDs must be absent. Search for the actual private
   identifiers and path fragments from the finding, including slash variants, as well as
   recognizable identifier patterns. Then read for paraphrased private incident details that
   a string search cannot detect. Keep provenance only in `RETRO.md`. If the practice cannot
   be explained safely and independently, retain eligibility with a private hold.
5. Prepare the local root `RULES.md` diff automatically in that clean, target-based checkout;
   create the file only if absent, preserving
   unrelated content. Do not overwrite another writer's changes or switch a dirty checkout.
   If a safe local edit is unavailable, persist the exact public patch privately as the one
   pending proposal and report where it can be applied. Preparation grants no push, PR, merge,
   release, or publication authority. Use only separately established delivery authority.

Persist the proposal identity and exact public text or patch before applying the edit, with
`promotion.status: pending`. After applying, read back the public diff and record its fingerprint.
On interruption, compare the saved proposal with the actual section/diff before applying anything.
If already present, reuse it. A rerun never appends a second section, creates another proposal,
or changes recurrence. If a pending PR exists, leave its matching proposal alone. A closed
unmerged PR stays pending with its disposition; do not repeatedly reopen or regenerate it.
Changed wording amends the same proposal and retains its prior revisions in private history.

For an equivalent rule already accepted on the target branch, no public edit is needed.
Record a reuse proposal. Its presence at a verified target OID establishes repository acceptance
for reuse without a prior PR lookup. Verify the equivalent section at that OID and record that
commit's date as `adopted_at`, with history action `reuse`. An unrelated local checkout or stale
tracking ref does not establish the target OID. This path applies only to an equivalent rule
already accepted when preparing the reuse proposal: never relabel a pending add/amend proposal
as reuse to bypass its PR acceptance checks, including after rejection or unmerged closure.

## Reconcile acceptance on a later pass

Reconcile recorded pending proposals even when capture has no changed evidence. Inspect only
their recorded repository, target branch, public section, and PR; do not scan all PR history
or add a merge watcher, polling hook, or background job. At most one bounded merge-state
lookup per recorded PR per invocation is needed; share its result across matching findings.
When `promotion.pr` is null for an add/amend proposal, make one bounded read-only identification
attempt per proposal per invocation. At the verified target OID, find the commit introducing
the fingerprinted rule section: for example, inspect at most 50 commits with
`git log -n 50 -S <distinctive-public-text> <target-oid> -- RULES.md` (or `-G`), verifying the
section against the saved public text/fingerprint rather than trusting a search hit. Use the
host's commit-to-PR lookup, such as `gh api repos/<owner>/<repo>/commits/<sha>/pulls`, for that
one matching commit; inspect one bounded response, without scanning all PR history. Match the
repository, target, and actual accepted change, then persist the identified PR in `promotion.pr`
before applying the existing adoption checks below unchanged. A delivery workflow may also
supply that identity. Missing objects, no match within the bound, truncation, or multiple
ambiguous matches leave a private gap and pending state. Retry only on a later invocation;
this skill does not open a PR or start polling to discover its state.

Use read-only evidence such as
`gh pr view <pr> --repo <repository> --json state,mergedAt,mergeCommit,baseRefName,url`
and, when the objects are locally available,
`git merge-base --is-ancestor <merge-oid> <target-ref>`.
Check command exit status: ancestry exit 1 means not an ancestor; other failures are gaps.
Inspect the accepted `RULES.md` section using `git show <target-oid>:RULES.md` or a bounded
read-only hosting API request. Record the exact target OID inspected and the evidence source.
Do not infer acceptance from an unrelated local HEAD or a stale tracking ref. A read-only
hosting response may establish the target snapshot and reachability when local objects are
unavailable; no fetch, push, or branch mutation is required by this procedure.

For add/amend proposals, adoption requires all of: the recorded PR is actually merged, its repository and base match
the intended target, its non-null merge commit and merge timestamp are established, that merge
is observed on the target branch, and the accepted public section contains the intended rule
or a semantically equivalent reviewed amendment. A squash/rebase merge uses the hosting
provider's accepted commit, not ancestry of the original proposal commit. A merged PR that
dropped the rule is not adoption. If the target later removed or contradicted the rule, record
that discrepancy and hold reconciliation rather than assert current authority from old text.

Apply this decision table only after those checks. `verified` means every add/amend adoption
condition above passed; `reuse_verified` means the already accepted equivalent section was
verified at the target OID as described above. Approval is deliberately irrelevant. This is
a contract table, not a scheduler.

```yaml
acceptance_states:
  pending: pending
  approved: pending
  closed_unmerged: pending
  merged_wrong_target: pending
  merged_rule_missing: pending
  merged_unverified: pending
  verified: promoted
  reuse_verified: promoted
```

Approval alone, a pending PR, and a PR closed unmerged never mark promotion. Integration into
a delivery branch never marks promotion. Query errors, absent objects, or ambiguous evidence
also leave the proposal pending with a gap; do not retry indefinitely in this pass.

On verified acceptance, atomically set `promotion.status: promoted`, `destination` to the public
repository's `RULES.md` section (prefer a commit-pinned URL), and `adopted_at` to the actual
merge timestamp, not today's retrospective date. Append the acceptance evidence to private
history only once, keyed by repository, target, PR, merge OID, and section. Keep the observation
time separately. A repeated reconciliation is a no-op. For a reused rule, record the verified
target commit's date instead of a merge timestamp, and mark the history action `reuse` with
the target OID and section as its acceptance key; no PR or fictional merge is needed.
`RULES.md` is now the authority; the notebook retains the evidence and promotion history.

## Resolve holds

On each later invocation, recheck a fixable hold's recorded condition once within the same
read-only bounds. When the missing checkout, source evidence, or safe wording becomes available,
record the resolution, clear `hold`, and retry the same proposal; preserve its identity and
history. A conflict with established rules or acceptance criteria requires the recorded human
decision before clearing the hold. Do not treat elapsed time or recurrence as that decision.

A held proposal that subsequently merges still undergoes all adoption checks. If the accepted
text resolves the hold (including any required human decision), record that resolution, clear
the hold, and promote once; otherwise keep it pending with the unresolved reason even though
the PR merged. A rejected or closed-unmerged PR remains pending with a rejection/closure hold.
Do not repeatedly prepare, reopen, or replace that proposal. Retry preparation only after a
new explicit human direction resolving that disposition; use the same proposal and retain the
old PR in history. Read-only reconciliation may still observe a genuine later merge/reopening,
but neither rejection, approval, nor closure alone establishes acceptance.
