# Public rule promotion

Use the finding's dated evidence and `Seen` line in private `RETRO.md`. Three distinct supported
days establish eligibility. Several observations on one day count once; copied reports and
reruns add neither a day nor a rule. If the dates and count disagree, retain a hold and report
the gap; do not invent dates. Personal preferences stay in `.brain/AGENTS.md` even if recurring.

## Resolve delivery authority

Read `retro.promotion` directly from private `project.yaml`. This is a skill setting, not a CLI command:

```yaml
retro:
  promotion:
    auto-deliver: false
    destinations: []
```

Missing settings mean disabled. Only YAML boolean `true` enables auto-delivery. Malformed or
unreadable configuration grants no authority; report the gap and continue private capture.
`destinations` is an allowlist of existing public file paths relative to the identified repo,
such as `RULES.md`, `CONTRIBUTING.md`, or `docs/code-standards.md`. Reject empty/non-string
entries, absolute paths, traversal, private context, and symlinks escaping the checkout.
A missing, scalar, or empty array blocks auto-delivery; the former singular setting grants
no authority. Select the best fit by subject and scope, not every file in the list. Ambiguous
ownership or no suitable file leaves a private suggestion; do not expand the allowlist.

- **Disabled/unset:** discover repository rules, standards, and contributor conventions. Suggest
  the file, practice, rationale, and observable review check privately and in the report. No public
  edits, commits, pushes, or PRs. The user may authorize that specific proposal and destination
  without enabling future delivery. Nightly runs report suggestions without waiting for a reply.
- **Enabled:** validate allowed destinations, inspect accepted guidance and open proposals,
  then prepare and deliver appropriate changes. This grants standing commit/push/PR authority
  only for this repository and those files. Missing or unsuitable files block delivery, not capture.

Creating a new file requires explicit human agreement to that file; a configured path alone
does not authorize creation. An existing `RULES.md` does not itself enable delivery. Disabling
auto-delivery stops public mutations, including PR updates, unless specifically authorized.
Read-only reconciliation continues in either mode. Approval, merge, and release stay human-owned.

## Prepare an authorized proposal

1. Identify the upstream target repository/base branch, verified target commit, push repository
   (the same repo or an existing authorized fork), proposal head branch, chosen file, and delivery
   authorization. Follow [PR delivery](pr.md) to resolve authentication, identities, and permissions on
   both repositories. A delivery/integration branch is not the acceptance target. Record these
   with the finding's `Proposal:` note. Without authority, keep a `Suggestion:` instead.
2. Compare accepted rules and open target-branch PRs by situation and required behavior.
   Reuse an equivalent rule or public proposal; amend existing guidance when needed. Several
   findings can share one proposal. Never overwrite another contributor's branch. Conflicting
   guidance or public proposals become a `Hold:` for resolution; recurrence never overrides
   an established rule or acceptance criterion. Incomplete proposal discovery blocks delivery.
3. Derive fresh public wording with a trigger, required behavior, and enough rationale to stand
   alone in an ordinary clone. Follow [the rule format](rules.md), preserving existing conventions.
   Use repository concepts, not private incident narratives or recurrence counts as proof.
4. Inspect the complete proposed diff and delivery text for private paths, Bead IDs, design/review
   identifiers, private evidence, and paraphrased private incidents. Search known identifiers and
   path variants, then read for leaks a search cannot detect. Keep provenance only in `RETRO.md`.
   If a safe, independently understandable rule is unavailable, retain a private hold.
5. Prepare only the agreed file changes in a clean checkout/worktree based on the verified target.
   Never edit rules on an unrelated feature branch. Preserve unrelated content. If a safe checkout
   is unavailable, keep the public wording or patch privately and report the blocker.

Before public edits, save the intended wording/patch and target with the finding, marked pending.
Record the proposal branch before pushing and the PR URL as soon as confirmed. On interruption,
compare the saved wording, existing file diff, remote branch, and PR before repeating an action.
Reuse existing work; a retry never adds another rule or changes recurrence. Changed wording updates
the same proposal; retain meaningful prior disposition and links. Independent private notebooks
need no synchronized counter: accepted guidance and public PRs are the shared coordination surface.

For an equivalent rule already accepted when first considering the finding, no edit or PR is
needed. Verify its section at the target commit and record `Accepted:` with the public link,
commit, and that commit's date, marked as reuse. Never relabel a pending or rejected proposal
as reuse to bypass its PR acceptance checks.

## Deliver

Follow [run-retro's PR process and body](pr.md), independent of the ordinary `pr` skill. Keep the
proposal pending until the actual upstream acceptance checks below succeed. Missing required authentication,
identity, or repository permissions block delivery only; private capture remains available.

## Reconcile acceptance

Inspect recorded proposals even when capture found nothing new, at most one bounded read-only
merge-state lookup per recorded PR per invocation. Share results for findings using the same PR.
For example, use `gh pr view <pr> --repo <repository> --json state,mergedAt,mergeCommit,baseRefName,url`.
Inspect the accepted section at a verified target commit using
`git show <target-commit>:<destination>` or a bounded read-only hosting API. Where objects exist,
`git merge-base --is-ancestor <merge-commit> <target-ref>` checks reachability (exit 1 means not
an ancestor; other failures are gaps). Do not trust an unrelated HEAD or stale tracking ref.

Adoption requires the actual merged PR, matching repository/base, known merge commit and time,
that merge on the acceptance target, and the intended rule or semantically equivalent reviewed
wording still present there. Squash/rebase merges use the host's accepted commit. A merged PR
that dropped the rule is not adoption. Approval, unmerged closure, a delivery-branch integration,
query failures, or ambiguous evidence never establish acceptance.

If an interrupted delivery lacks its PR URL, make one bounded read-only lookup by the recorded
head repository and branch against the recorded upstream/base. If unavailable, inspect at most
50 target commits affecting the destination for the
intended rule and use the matching commit's PR lookup. Ambiguity or no match leaves the proposal
pending with a gap; no all-history scan, merge watcher, background job, or polling.

After verified adoption, add `Accepted:` with the public section link (prefer commit-pinned),
PR, merge commit, and actual merge date beside the original finding. Keep it in its work-area
section; no separate promoted section or human notification is required. Do not use today's
run date as the adoption date. Reconciliation never changes evidence dates, Seen count, or capture
progress. An unchanged lookup adds no history bullet. If target guidance later removes or
contradicts the rule, report the discrepancy rather than assert current authority from old text.

## Holds and dispositions

Record blockers beside the proposal with enough context to resume once the condition changes.
Recheck a fixable condition once per later pass; preserve previous PR links and decisions.
Conflicts with rules or acceptance criteria require the human's decision. A rejected or
closed-unmerged proposal remains unadopted with a hold; do not regenerate or reopen it without
new explicit direction. A later genuine merge still needs every acceptance check and must
resolve any hold. If evidence later falls below the threshold, record a hold and preserve the
proposal/adoption history; do not automatically erase a public rule.
