# Public rule promotion

Use the saved capture contract, not retrospective run dates: `evidence_dates` is the unique
set of supported evidence days and `distinct_days` its size. Several observations on one day
count once; copied reviews and reruns add neither a day nor a rule. Resolve finding redirects
before looking up proposals. If the saved count and dates disagree, hold preparation and
report the capture gap; do not invent dates or silently repair capture here.

## Prepare one change

For each eligible finding with at least three supported days:

1. Identify the public repository and intended target branch explicitly from the existing
   delivery context. A delivery/integration branch is not the acceptance target. If the checkout
   or target cannot be identified, retain eligibility and record a hold. This procedure provides
   no alternate rules destination for a project without a repository.
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
5. Prepare the local root `RULES.md` diff automatically; create the file only if absent, preserving
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
Record a reuse proposal and verify its prior human PR acceptance using the reconciliation
checks below. Local presence or ancestry alone is not proof of that boundary. Without its
acceptance evidence, keep the reuse pending rather than asserting adoption.

## Reconcile acceptance on a later pass

Reconcile recorded pending proposals even when capture has no changed evidence. Inspect only
their recorded repository, target branch, public section, and PR; do not scan all PR history
or add a merge watcher, polling hook, or background job. At most one bounded merge-state
lookup per recorded PR per invocation is needed; share its result across matching findings.
Missing PR identity or unavailable evidence leaves a private gap and pending state, not a
guessed acceptance. A PR attached through an already authorized delivery workflow supplies
identity; this skill does not open one to discover its state.

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

Adoption requires all of: the recorded PR is actually merged, its repository and base match
the intended target, its non-null merge commit and merge timestamp are established, that merge
is observed on the target branch, and the accepted public section contains the intended rule
or a semantically equivalent reviewed amendment. A squash/rebase merge uses the hosting
provider's accepted commit, not ancestry of the original proposal commit. A merged PR that
dropped the rule is not adoption. If the target later removed or contradicted the rule, record
that discrepancy and hold reconciliation rather than assert current authority from old text.

Apply this decision table only after those checks. `verified` means every adoption condition
above passed; approval is deliberately irrelevant. This is a contract table, not a scheduler.

```yaml
acceptance_states:
  pending: pending
  approved: pending
  closed_unmerged: pending
  merged_wrong_target: pending
  merged_rule_missing: pending
  merged_unverified: pending
  verified: promoted
```

Approval alone, a pending PR, and a PR closed unmerged never mark promotion. Integration into
a delivery branch never marks promotion. Query errors, absent objects, or ambiguous evidence
also leave the proposal pending with a gap; do not retry indefinitely in this pass.

On verified acceptance, atomically set `promotion.status: promoted`, `destination` to the public
repository's `RULES.md` section (prefer a commit-pinned URL), and `adopted_at` to the actual
merge timestamp, not today's retrospective date. Append the acceptance evidence to private
history only once, keyed by repository, target, PR, merge OID, and section. Keep the observation
time separately. A repeated reconciliation is a no-op. For a reused rule, record its original
verified acceptance date and mark the history action `reuse`, not a fictional new merge.
`RULES.md` is now the authority; the notebook retains the evidence and promotion history.
