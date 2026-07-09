<p align="center">
  <img src="docs/assets/banner.jpg" alt="Dotbrain" width="100%">
</p>

# Dotbrain

> Dotbrain keeps your project's context private and your code repo clean, and makes that discipline effortless.

As an engineer, almost everything I build outgrows my private workspace. A side project I start
alone gets shared or open-sourced later; team repos are visible from day one. The code can be
shared; the thinking behind it doesn't have to be: the half-formed decisions, the roadmap, the
rationale I would not want published, or leaked into a commit message by an agent.

For a while that thinking had no natural home. It scattered across my head, my Obsidian vault,
gitignored docs, and agent memory layers. Keeping it coherent was its own maintenance job. Every
new session meant re-explaining the project, re-wiring tools, and hunting for context that should
have just been there. So I built Dotbrain.

## What is Dotbrain?

Dotbrain keeps your project's private thinking in a versioned Brainspace under `~/dotbrain/`.
It plants gitignored symlinks at your repo root pointing into that Brainspace, so agents pick
up your decisions, vocabulary, and notes automatically at session start. The content never
touches the code repo; the symlinks make sure it follows the project wherever you work it.

    ~/dotbrain/
    └── brainspaces/
        └── my-project/
            ├── .brain/
            │   ├── CONTEXT.md  # domain vocabulary
            │   ├── adr/        # architecture decisions
            │   ├── designs/    # design docs
            │   └── docs/       # derived reference material
            ├── .beads/     # execution store (issue tracker)
            ├── .claude/    # Claude Code workspace
            └── .codex/     # Codex workspace

    ~/repos/my-project/     (gitignored symlinks in your code repo)
    ├── .brain  ──────────────► ~/dotbrain/brainspaces/my-project/.brain
    ├── .beads  ──────────────► ~/dotbrain/brainspaces/my-project/.beads
    ├── .claude ──────────────► ~/dotbrain/brainspaces/my-project/.claude
    └── .codex  ──────────────► ~/dotbrain/brainspaces/my-project/.codex

## Why not just keep private notes?

A gitignored notes file is the obvious fix, but I wanted those notes versioned, so they became a
separate private repo. That is what I did for a long time. It kept them private and tracked, but it
sat off to the side of the project: when I spun up a git worktree to run a second agent in parallel,
the notes did not come with it; when I cloned the project onto another machine, they were not there
either. The context I needed most was the context that never followed the work.

Dotbrain keeps the Brain, the issue tracker, and agent configs all private and versioned under a
project's Brainspace, wired into the repo from a single private home. A worktree picks it up automatically. A new machine is one clone and bootstrap away
from having every project wired. The notes are there wherever you work the project, instead of
sitting beside it.

## "But my agent already remembers, and I have CLAUDE.md/AGENTS.md"

**Agent session memory** carries context between sessions, but it is person-scoped, not
project-scoped: it accumulates facts about you, not the decisions and rationale behind a specific
project. Memory banks have the same shape. Both are also vendor-locked: Claude's memory doesn't
help Codex, and wiring a new agent into a project means manual setup each time. Dotbrain is owned
by the project, not the person or the tool: any agent working in the repo picks it up
automatically.

**CLAUDE.md/AGENTS.md** is great for a handful of standing instructions, but it lives in the public
repo and should not become the home for every decision and design note. Past a point it just bloats,
and everything in it is public if the repo is.

Dotbrain is a project's private source of truth: authored by humans, readable by any agent,
enforced by the wiring. The project brain is not accumulated; it is written, reviewed, and corrected.
Both the human and the agent work from the same source, and git tracks all of it.

## Is this for you?

**Use Dotbrain if:**

- you work with more than one coding agent or across multiple worktrees on the same project
- your project has real context worth preserving: decisions, vocabulary, rationale that agents need to work effectively
- your code is shared or will be, and you want the thinking behind it to stay private
- you want that context authored and version-controlled, not accumulated in an opaque tool

**Skip it if:**

- your repos are all private and a single agent already covers you
- you only need a few standing instructions; `CLAUDE.md` is genuinely simpler
- you are looking for a hosted team knowledge base

## How it works

```mermaid
flowchart LR
  agent(["Coding agent: Claude Code, Codex"])
  subgraph repo["Code repo"]
    direction TB
    code["your code"]
    links["gitignored symlinks"]
  end
  subgraph home["Private dotbrain home (~/dotbrain)"]
    direction TB
    brain["Brain: vocabulary, decisions, rules"]
    exec["Execution store: ready-work tracker"]
    ws["Agent workspaces"]
  end
  agent --> repo
  links --> brain
  links --> exec
  links --> ws
```

`dotbrain wire <repo>` creates the Brainspace, drops gitignored symlinks at the repo root, and
links project skills and subagents into the agent workspaces. `dotbrain refresh` repairs wiring
and relinks project skills and subagents if anything drifts. `dotbrain bootstrap` runs once per
machine to install session-start hooks and link global skills and subagents.

**Skills** are cross-project and live under `~/dotbrain/skills/`. Wiring links the relevant ones
into each agent workspace (`.claude/`, `.codex/`) so any agent in the repo gets the same skill
set without manual setup. Per-project skill and subagent selection lives in `project.yaml`; the
Brain's `AGENTS.md` holds the cross-cutting conventions those skills read at session start.

**Beads** (`.beads/`) is the private execution store. Agents use the `bd` CLI to inspect ready
work, claim issues, and close them. Because it lives in the Brainspace and is version-controlled,
any agent across sessions, worktrees, or tools operates from the same issue tracker. Work claimed
in one session is visible to the next; nothing is re-derived from scratch.

The session-start hook loads Brain context and execution state automatically, so every session
starts warm: the agent knows the project vocabulary, the standing decisions, and what work is
ready.

When something needs to go public, you author a fresh, audience-specific doc rather than copying
from the Brain, a private source that should never be mirrored into the code repo.

## Workflow

Dotbrain ships a set of bundled Brain-coupled skills: the operating manual for a wired project. They load
automatically at session start and are available as slash commands.

- **`wire-brain`** — provision or repair Brainspace wiring between a repo and its private Brain.
- **`grill-decisions`** — stress-test a plan against the project's vocabulary and existing
  decisions, then write clarified choices into `CONTEXT.md` and `adr/`.
- **`build-context`** — draft or normalize `AGENTS.md` and related agent context files.
- **`operate-execution`** — inspect the ready frontier, claim a work item, and record discoveries
  back into the execution graph. This is the primary skill for driving daily work.
- **`to-design`** — formalize a multi-step initiative into a design doc, save it to the Brain, and
  create an epic bead.
- **`to-issues`** — decompose a design doc into independently-workable bead tasks with acceptance
  criteria and dependencies.
- **`review-architecture`** — review the codebase for deeper architectural opportunities and feed
  findings back into the Brain.
- **`triage-public`** — intake public issues (GitHub, Linear, Jira), classify them, and link
  accepted work to private execution items.

See [docs/skills.md](docs/skills.md) for the full set.

### Worktree execution

Most work runs in place in the main checkout, reviewed as it happens. When work needs isolation,
such as genuine parallelism or a long-running loop you want off your interactive tree, run it in a
git worktree instead. A worktree shares the same Brainspace, Brain, and execution state as the main
checkout through the same symlinks, with no separate Brain and no re-wiring.

`operate-execution` recommends when to isolate; the agent runtime provides the worktree. Start a
full worker session in one with the launcher:

```bash
dotbrain codex --worktree <bead-id>-<slug>
```

## Install

```bash
git clone https://github.com/arminzou/dotbrain.git
cd dotbrain
./install.sh        # installs uv, Beads (bd), and the dotbrain CLI
dotbrain bootstrap  # install agent hooks and link global skills
```

## Use

```bash
dotbrain wire <repo>      # connect a code repo to a private Brainspace
dotbrain refresh          # repair wiring, load execution state, link project skills
dotbrain unwire <repo>    # disconnect a repo from its Brainspace
```

## Develop

The CLI is a [uv](https://docs.astral.sh/uv/)-managed Python package.

```bash
uv sync                 # provision the env
uv run dotbrain --help  # inspect the command tree
uv run pytest           # run the test suite
```
