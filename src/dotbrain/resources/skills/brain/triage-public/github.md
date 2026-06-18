# Issue tracker: GitHub

Public issues live as GitHub issues. Used by `triage-public` when `public-tracker: gh` is set in
`project.yaml`. Use the `gh` CLI for all operations. `gh` infers the repo from the adopter remote
when run inside a clone; use `public-tracker-id` (`<org>/<repo>`) from `project.yaml` only when it
is explicitly set.

## CLI conventions

- **Create**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read**: `gh issue view <number> --comments`.
- **List**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with `--label` / `--state` filters as needed.
- **Search**: `gh issue list --search "keyword in:title"`.
- **Comment**: `gh issue comment <number> --body "..."`.
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`.
- **Close**: `gh issue close <number> --comment "..."`.

## Triage loop

1. List open issues to survey.
2. Classify each: bug / feature / question / duplicate / wontfix.
3. Apply labels and milestones via `gh issue edit`.
4. For anything that needs execution tracking, record it into the private engine and link it
   (`operate-execution`): create a work item, then `bd update <id> --external-ref gh-<number>`.
5. Comment on the issue when acknowledgement is warranted.

The public/private link is one-directional: the private work item holds the `gh-<number>`
reference. A PR `Closes #N` closes the public issue only; the private work item still needs
explicit close. Project linking discipline lives in `.brain/agents/issue-tracker.md`.

## Skill-phrase mappings

- **"publish to the issue tracker"** — create a GitHub issue.
- **"fetch the relevant ticket"** — `gh issue view <number> --comments`.
