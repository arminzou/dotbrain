<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/public/assets/lockup-horizontal-dark-1024.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/public/assets/lockup-horizontal-light-1024.png">
    <img src="docs/public/assets/lockup-horizontal-light-1024.png" alt="Dotbrain" width="480">
  </picture>
</p>

# Dotbrain

English | [简体中文](README.zh-CN.md)

[![PyPI](https://img.shields.io/pypi/v/dotbrain?style=flat&logo=pypi)](https://pypi.org/project/dotbrain/)
[![CI](https://img.shields.io/github/actions/workflow/status/arminzou/dotbrain/ci.yml?branch=main&style=flat&logo=github&label=CI)](https://github.com/arminzou/dotbrain/actions/workflows/ci.yml)
[![Python](https://img.shields.io/pypi/pyversions/dotbrain?style=flat&logo=python)](https://pypi.org/project/dotbrain/)
[![License: MIT](https://img.shields.io/badge/license-MIT-117967?style=flat)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-read-117967?style=flat)](https://arminzou.github.io/dotbrain/)

**Private project context for Claude Code and Codex.**

Dotbrain brings the Dotfiles convention to your project work. Keep your working notes, plans,
instructions, and selected agent resources in a private home, then wire them into the checkouts
where you work.

Your context stays in local files with its own Git history. The CLI connects your workspace to
the code repo; the plugin's workflow skills guide how your agent uses and maintains it with you.

[https://github.com/user-attachments/assets/540e8945-b8bc-4fc1-ac05-c125bf768fa9](https://github.com/user-attachments/assets/021fc13a-db20-4549-8aab-b5240d289bde)

[Documentation](https://arminzou.github.io/dotbrain/) ·
[Getting started](https://arminzou.github.io/dotbrain/getting-started) ·
[The workflow](https://arminzou.github.io/dotbrain/workflow)

### Why I built it

Global agent instructions describe how I want my agent to behave at user level. Shared repository instructions
describe how anyone should work on the code. My own reasoning, working notes, and plans for a
particular project need a private home.

Mine were scattered across Obsidian, gitignored notes, and agent memory. Finding that context and
bringing it into another session took effort. So did making my selected skills and subagents
available in a new checkout. I built Dotbrain to keep that project workspace together and make
connecting it to where I work repeatable.

Read the story behind Dotbrain: [Dotfiles for Your Repo](https://x.com/i/article/2109385521214390273).

## Is this for you?

Use Dotbrain when you need a private project workspace you want to keep developing across
agents, sessions, or worktrees: context you've built up, plans in progress, and your own
instructions and selected skills for the work.

It works alongside your agent's memory system and other context tools. The workspace is yours;
you decide which outcomes belong in shared repository docs or public proposals.

If a few standing instructions in `AGENTS.md` or `CLAUDE.md` cover your needs, keep it simple.

## Get started

Install the plugin into your coding agent. You do not need to clone this repo.

**Claude Code** — send these as two separate prompts:

```text
/plugin marketplace add arminzou/dotbrain
/plugin install dotbrain@dotbrain
```

**Codex:**

```bash
codex plugin marketplace add arminzou/dotbrain
codex plugin add dotbrain@dotbrain
```

In Codex, open `/hooks`, trust the dotbrain hook, then start a new thread.
[Hermes](https://arminzou.github.io/dotbrain/getting-started#hermes),
[OpenCode](https://arminzou.github.io/dotbrain/getting-started#opencode),
[Pi](https://arminzou.github.io/dotbrain/getting-started#pi), and
[Cursor](https://arminzou.github.io/dotbrain/getting-started#cursor) are supported through the CLI rather
than a marketplace.
On Windows, enable
[Developer Mode](https://learn.microsoft.com/windows/apps/get-started/enable-your-device-for-development)
before wiring so Dotbrain can create directory symlinks without Administrator privileges.

Then ask your agent:

```text
Use wire-brain to wire this repo with Dotbrain.
```

The skill installs the matching CLI, `uv`, and Beads if needed, prepares the machine, and wires
the repo to its private Brainspace. Check the result with:

```bash
dotbrain doctor
```

Start a fresh agent session in the wired repo to load the Dotbrain convention. It tells the
agent where to find your project context and how to work with it.
See [Getting started](https://arminzou.github.io/dotbrain/getting-started) for manual installation,
backups, a second machine, and troubleshooting.

### Update

Update the plugin and the CLI together. In Claude Code, run `/plugin`, update dotbrain from the
menu, then `/reload-plugins`. In Codex:

```bash
codex plugin marketplace upgrade
codex plugin add dotbrain@dotbrain
```

Then upgrade the CLI and reconcile your machine and projects:

```bash
uv tool install dotbrain@latest
dotbrain bootstrap
dotbrain refresh --all
```

Installed the CLI with pipx or pip? Upgrade with that tool instead. See
[Staying current](https://arminzou.github.io/dotbrain/getting-started#staying-current).

## How it works

Each project has a **Brainspace** under your private dotbrain home, by default `~/dotbrain/`.
It holds the **Brain** (`.brain/`: local Markdown files for project rules, vocabulary, decisions,
and designs) and an **execution store** (`.beads/`: issues tracked with
[Beads](https://github.com/gastownhall/beads)). Gitignored symlinks make both available through
the checkout while their files and history stay outside the code repo.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/public/assets/how-it-works-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="docs/public/assets/how-it-works-light.png">
  <img src="docs/public/assets/how-it-works-light.png" alt="Claude Code and Codex work in the code repo. Gitignored links connect it to a separate private Brainspace holding the Brain and Beads." width="1000">
</picture>

Wiring also delivers selected skills and subagents into the repo's agent workspaces, `.claude/`
and `.codex/`. Skills and Claude agents use symlinks; Codex agents use generated, Git-ignored
TOML files. Wiring a Git worktree connects it to the main checkout's existing Brainspace, so
both use the same knowledge and tracker.

At session start, the plugin hook supplies only `DOTBRAIN.md`, the shared convention.
Public `AGENTS.md` routes making or reviewing changes to tracked root `RULES.md`, usable
without a Brain. The lead or sole agent searches private retrospective findings for the task
and passes relevant findings through assignments; the notebook is never injected.
Fresh Brains seed private `AGENTS.md` for a small set of personal preferences and project
rules, with `CLAUDE.md` as its alias. The agent reads it before substantial work; it is
never injected. Wiring and refresh preserve user-owned context and existing pointers.
Public `RULES.md` holds repository requirements; private preferences stay private.
See [Session context](https://arminzou.github.io/dotbrain/session-context) for the loading sequence.

Use `dotbrain projects list` to discover registered projects. Inside a wired checkout,
`dotbrain refresh` maintains that checkout and `dotbrain unwire` detaches it while retaining the
shared Brainspace. From elsewhere, select `--project <name>`; use `refresh --all` for registered
projects. Machine-global asset reconciliation is explicit: `skills link --scope global` or
`agents link --scope global`.

Git versions the Brain. Back it up to a **private** remote; the Beads database is Git-ignored
and needs its own Dolt remote or shared server to back up or share issues.
See [Architecture](https://arminzou.github.io/dotbrain/architecture),
[Wiring](https://arminzou.github.io/dotbrain/wiring), and
[Beads backend](https://arminzou.github.io/dotbrain/beads-backend) for details.

## The loop

Every piece of work should leave the next session better informed. Dotbrain's bundled skills
carry work from idea to implementation, then return what you learned to the project's context.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/public/assets/workflow-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="docs/public/assets/workflow-light.png">
  <img src="docs/public/assets/workflow-light.png" alt="Workflow skills guide work through decisions, design, issues, execution, review, and closure. Discoveries update the active design; lasting decisions return to the Brain for the next initiative." width="880">
</picture>

The loop closes in two places:

- **During the work:** discoveries feed back into the active design and affected issues. An
  unexpected API constraint becomes a design question; once you settle it, the design and issues
  capture the decision before implementation continues.
- **After human merge and manual closeout:** closing the design records the evidence and preserves useful decisions and
  vocabulary in the Brain. The next initiative starts with that knowledge already available.

The Brain holds durable knowledge, the design holds current intent, and Beads holds execution
state. Each handoff lives in a document or tracker entry that another session or agent can
consult to continue the work.

You own success criteria, PR approval, merge, and release. Settle foreseeable decisions and the
execution contract upfront; agents reuse complete applicable approval without another routine
sign-off and work through checks, acceptance/UAT, and required reviews to a ready PR requesting
your review. New scope, authority, or criteria decisions stop affected work with evidence and a
recommendation. Limits survive resume. The design stays active until you invoke closeout;
a PR closed without merge does not establish shipment. Use the full loop when work spans
sessions or carries open questions; small changes can use just the steps they need.

See [The workflow](https://arminzou.github.io/dotbrain/workflow) for a walkthrough and
[Skills](https://arminzou.github.io/dotbrain/skills) for the full catalog.

## Develop

The CLI is a [uv](https://docs.astral.sh/uv/)-managed Python package.

```bash
git clone https://github.com/arminzou/dotbrain.git
cd dotbrain
uv sync
uv run dotbrain --help
uv run pytest
```

For an editable CLI, run `./scripts/dev-install.sh` (or `.\scripts\dev-install.ps1` on Windows),
then `dotbrain bootstrap`. Bundled skills are authored in [`plugin/skills/`](plugin/skills/).
See the [CLI reference](https://arminzou.github.io/dotbrain/cli-reference) for commands and options.

For bug reports and pull requests, see [Contributing](CONTRIBUTING.md).

Released under the [MIT License](LICENSE).
