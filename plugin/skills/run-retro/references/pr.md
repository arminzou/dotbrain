# Rule-proposal PR delivery

Read only when [promotion](promotion.md) establishes delivery authority. This is run-retro's own
process and PR shape; do not invoke the ordinary `pr` skill or inherit its handoff workflow.

## Resolve authentication and repositories

Use the repository's established hosting and authentication setup. For GitHub, standard `gh`
and `git` are sufficient; this skill requires no separate `pr` skill, custom script, or GitHub
App. Confirm the selected identity is authorized by the user/project for delivery. An existing
login alone does not grant push/PR authority; [promotion](promotion.md) resolves that separately.

If project instructions require an App, bot, connector, or custom helper, use that mechanism
for the applicable commands instead of the plain CLI examples below. Discover its location
and usage from those instructions, not another assumed skill installation. If the required
mechanism is unavailable, retain a delivery blocker; do not switch identities or fall back to
another login. Never print credentials or copy them into prompts, public files, or the notebook.
If the host is not GitHub, use its established equivalent tools or report missing delivery support.

Resolve and record these explicitly from verified remotes, repository metadata, and existing
authorization; do not assume `origin` means upstream:

| Identity | Same-repository delivery | Fork delivery |
| --- | --- | --- |
| Target repository/base | Repository receiving the PR and its acceptance branch | Upstream repository and its acceptance branch |
| Push repository/head | Same repository and a dedicated proposal branch | Existing authorized fork and a dedicated proposal branch |
| PR head selector | Branch name | Fork owner plus branch, `owner:branch` |

The proposal branch starts at the verified upstream/base commit, not the fork's default branch.
Auto-delivery applies to proposals against the identified project; it does not authorize creating
a fork or selecting an unrelated push repository. Use an existing configured/authorized fork or
record a blocker for the user's decision. Confirm the fork belongs to the target's repository
network. Confirm the selected authentication can push the proposal branch and can read and
open a PR against the target. Ordinary fork contributors need not have push access to upstream.
App installations and repository-scoped tokens may impose additional limits: credentials scoped
to the fork do not necessarily support PR actions on upstream. Validate both operations under
the configured mechanism; unavailable access leaves a blocker. Never push to the acceptance branch.

## Prepare and deliver

Use a descriptive dedicated branch containing only the agreed public rule changes. Related
rules may share one PR. Follow the repository's commit convention; keep private identifiers
out of names and messages. Before committing, inspect the diff and proposed body for privacy,
overlap, conflicts, and actionable checks. Respect applicable repository checks and report what
actually ran. Documentation alone does not require native agent UAT or a failing-before/passing-after
code test. Save the push repo/head and upstream/base privately before the first outward action.

The examples below use standard GitHub CLI authentication; fill variables from verified
context. `retro_pr_head` is the branch for same-repo delivery or `fork-owner:branch` for a fork.
Run from the proposal worktree, inspect each result, and stop on failure; these are separate
actions, not a script to run blindly. Apply project-specific credential requirements to reads
as well as writes. When a custom helper is required, invoke these operations through it.

```bash
gh auth status
gh repo view "$retro_push_repo" --json nameWithOwner,viewerPermission
gh repo view "$retro_target_repo" --json nameWithOwner,defaultBranchRef
gh pr list --repo "$retro_target_repo" --state all --base "$retro_base" --head "$retro_branch" --limit 100 --json number,url,state,author,headRepository,headRepositoryOwner,headRefName,baseRefName
git push "https://github.com/$retro_push_repo.git" "HEAD:refs/heads/$retro_branch"
gh pr create --repo "$retro_target_repo" --base "$retro_base" --head "$retro_pr_head" --title "$retro_title" --body-file "$retro_body_file"
```

First inspect the lookup response: reuse a matching owned open PR, leave an unchanged one alone,
and retain rejected/closed-unmerged proposals on hold. A merged match goes to reconciliation,
not another PR. Confirm both head repository and branch, upstream/base, and author; branch-name
matches alone are insufficient. An incomplete or ambiguous response is a blocker. Existing PRs
from other contributors may be reused as evidence but their branches/bodies are not edited.
For open-proposal semantic overlap, use promotion's wider target-branch search as well.
`pr list --head` takes a branch name, not `owner:branch`; inspect head repository/owner in
the returned records. If the lookup reaches its result limit, treat it as incomplete.

Create a ready-for-review PR only when no matching proposal exists. For an owned changed proposal,
push its update and edit that same PR. Request the configured human reviewer when available:

```bash
gh pr edit "$retro_pr" --repo "$retro_target_repo" --body-file "$retro_body_file"
gh pr edit "$retro_pr" --repo "$retro_target_repo" --add-reviewer "$retro_reviewer"
git ls-remote "https://github.com/$retro_push_repo.git" "refs/heads/$retro_branch"
gh pr view "$retro_pr" --repo "$retro_target_repo" --json url,state,isDraft,author,baseRefName,headRefName,headRefOid,headRepository,headRepositoryOwner
```

The same `gh`/`git` arguments work in PowerShell; run Windows automation in `pwsh -NoProfile`.
Use a body file for multiline text in either shell, for example:

```powershell
gh pr create --repo $retro_target_repo --base $retro_base --head $retro_pr_head --title $retro_title --body-file $retro_body_file
```

Never interpolate the body's contents into a shell command. When a custom helper is configured,
read its actual parameters rather than assuming Bash and PowerShell argument passing match.
Confirm Git push uses the intended configured identity as well; a `gh` login does not by itself
prove Git's credential helper uses that identity. Report mismatches instead of changing credentials.

Confirm remote head equals the intended commit and the PR's head, base, author, URL, and ready
state match the recorded identities. Fork PRs are accepted only through the upstream/base;
merging into the fork does not establish adoption. If the host/CLI cannot represent the selected
fork head, record the limitation rather than silently changing repositories or credentials.

After an uncertain push/create/update response, inspect the remote head and matching PR once
before retrying. If delivery fails or remains ambiguous, stop delivery for this invocation.
Do not force-push a shared branch, merge, add progress comments, post BLOCKED mentions, or poll.
Record confirmed PR URL, delivered commit, repository identities, and check results privately.

## PR body

```markdown
## Proposed rules
- <Rules being added or amended>

## Why
<Recurring failure pattern and why this repository needs these rules.
Use public-safe reasoning; private recurrence counts are not proof.>

## Review check
<How an agent or reviewer can determine whether a change follows each rule.>

## Existing guidance
<Why current rules are insufficient and how this proposal fits them.
Identify relevant public rules or proposals, checks actually performed, and limits.>
```

Cite public examples when available; disclose when no incident evidence is publicly inspectable.
Keep private provenance in `RETRO.md`. Map each proposed rule to its reason and review check.
Apply the dotbrain convention's human gates.
