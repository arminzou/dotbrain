# Issue tracker: GitHub

Public issues live as GitHub issues. Loaded by `triage-public` when `public-tracker: gh` is set in
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

## Triage roles as labels

The SKILL's roles are realized as GitHub labels. Each triaged issue carries exactly one category
and one state label:

- Category: `bug`, `enhancement`
- State: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`

Apply and swap them with `gh issue edit --add-label` / `--remove-label`. These labels live on the
**public** issue only. Private work uses the engine's native fields — when `operate-execution`
promotes an issue inward, it maps the role to a field, not a beads label (`bug`/`enhancement` →
`--type`, readiness → the dependency graph, `wontfix` → a close reason). See
[operate-execution/references/beads.md](../../operate-execution/references/beads.md).

## Triage loop

1. List open issues to survey.
2. Classify each: category (`bug` / `enhancement`) plus state.
3. Apply labels and milestones via `gh issue edit`.
4. For an accepted public issue that needs execution tracking, `operate-execution` records it into
   the private engine and sets an external reference back to `gh-<number>`.
5. Comment on the issue when acknowledgement is warranted.

The public/private link is one-directional and inward: the private work item holds the
`gh-<number>` reference for its public origin. Never create a GitHub issue from a private design,
epic, or bead just to track it publicly. A PR can provide a public review surface without an issue.
When a PR uses `Closes #N`, it closes the public issue only; the private work item still needs an
explicit close. Project linking discipline lives in the Brain's `AGENTS.md` (Project section).

## Skill-phrase mappings

- **"publish to the issue tracker"** — create a GitHub issue.
- **"fetch the relevant ticket"** — `gh issue view <number> --comments`.
