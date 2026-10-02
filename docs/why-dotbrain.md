# Why dotbrain?

You can give a coding agent useful project context without dotbrain. The question is whether
keeping that context connected, current, and private has become enough work to justify a tool.

## What do I get that my coding agent doesn't already provide?

Dotbrain gives you a consistent home for project knowledge and execution state, plus commands
to connect it to Claude Code and Codex. Your Brain holds vocabulary, decisions, working rules,
and designs. Selected skills and subagents are delivered into the agent's workspace.

For example, after recording why a project uses a particular database, a later session can read
that decision instead of asking you to reconstruct it. The plugin supplies the convention for
finding and using that material; you still have to capture the decision. Dotbrain does not replace
your agent or guarantee better code. See [Architecture](architecture.md).

## Couldn't I just use a separate private Git repo?

Yes. That already gives you private, versioned documents, and may be all you need.

Dotbrain adds the connection to your code checkouts: project selection, links into the right
Brainspace, skill and subagent delivery, shared context across worktrees, and commands to inspect
or repair the setup. You can build those conventions with scripts yourself. Dotbrain is useful
when you would rather maintain project knowledge than maintain that wiring.

## Why not just gitignore private context in my code repo?

Ignored local context can work well. Git does not version it, so you need to arrange its backup
separately. Both [Claude Code](https://code.claude.com/docs/en/worktrees#copy-gitignored-files-into-worktrees)
and [Codex](https://developers.openai.com/codex/app/worktrees/#copy-ignored-local-files-into-managed-worktrees)
support `.worktreeinclude` to copy selected ignored files into their local managed worktrees. If supplying
those files to new worktrees is all you need, the native mechanism may be enough.

Dotbrain puts the durable material in a separate private home and connects each checkout to the
same source, so edits to shared context are visible across wired worktrees without updating copies.
Detaching a checkout retains the Brainspace. Gitignore still protects the local links and delivered
resources from ordinary commits; the difference is where their source lives and how it is
reconnected. This is a storage and workflow boundary, not an access-control barrier: an agent
working in a wired checkout can read the linked material. See [Wiring](wiring.md).

## Why not use AGENTS.md and a few skills?

For public project instructions and a small set of stable preferences, that is a good starting
point. Dotbrain leaves project-owned runtime files in place and can work alongside that setup.

It earns its overhead when context grows beyond a short instruction file: decisions that need
their rationale preserved, designs spanning sessions, private runbooks, and resource selections
that need to stay consistent across checkouts. Its bundled skills guide that workflow, but you
do not need a design and an epic for every small edit. See [The workflow](workflow.md).

## Does dotbrain actually make an agent remember my project?

It preserves written context that a new session can retrieve. It does not preserve the model's
internal memory or load your entire project history into every conversation.

The session-start hook injects only dotbrain's shared convention. That convention directs the
agent to read project rules and retrieve relevant knowledge as needed. Hook activation depends
on the runtime, and an agent can still miss or misinterpret a document. Useful context needs
to be written, discoverable, and maintained. See [Session context](session-context.md).

## What changes when I use multiple agents or worktrees?

Claude Code and Codex can reach the same project Brain and execution store. A linked Git
worktree connects to its main checkout's Brainspace rather than getting a separate copy of
the context. Selected resources are delivered in the format each runtime uses.

For example, two worktrees can consult the same decision record while working on different
branches. They also share execution state, so claims and dependencies can help coordinate work.
For more advanced coordination using shared execution state, see
[Beads' multi-agent guide](https://beads.gascity.com/multi-agent).
That does not prevent code conflicts or concurrent edits to shared documents; agents still need
clear ownership. Across machines, you must also arrange private Git and tracker synchronization.

## What extra maintenance am I taking on?

The main ongoing work is keeping your project knowledge useful: record decisions, update rules
when the project changes, and remove stale guidance. That work exists with any approach to stored
context. Dotbrain maintains the CLI, plugin, shared convention, and resource delivery. Your setup
tasks are choosing skills and subagents, running `dotbrain refresh` when those selections change,
and using `dotbrain doctor` to check the wiring.

Tracker upkeep depends on your choice. Beads' **embedded local mode** is the default: there is no
separate server to maintain, and agents on one machine can use the shared store one writer at a
time. **Server mode** supports concurrent clients through a local or remote Dolt SQL server;
choosing it adds server operation to your setup. Across machines, configure a shared remote
server or Dolt remote synchronization. You can also use a tracker-free project if you manage work
elsewhere. See [Beads backend](beads-backend.md) and
[Beads' modes of operation](https://beads.gascity.com/architecture/dolt#modes-of-operation).

Backups are your choice. A private Git remote can back up your Brain documents; if you also want
tracker backups, arrange those separately. Pushing the documents does not back up the Beads database.

## When should I skip dotbrain?

Skip it when a small `AGENTS.md` and your agent's native skills already cover your needs, when
the work is short-lived, or when your private repo and linking scripts are easy to maintain.
Public project guidance that every contributor needs should remain in the code repo either way.

Consider dotbrain when you repeatedly explain the same decisions, lose context between sessions,
or repair private context and resources across agents and worktrees. Start with one project and
judge whether the saved effort outweighs the setup. [Getting started](getting-started.md) shows
what that involves.
