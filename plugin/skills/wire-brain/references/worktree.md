# Worktree repair

Restore a linked Git worktree's access to the main checkout's Brain and execution store, and link the
project's agent workspaces into it. This is a worktree-local repair: do not run `dotbrain wire`,
create a Brainspace, or copy either directory.

## Locate both checkouts

Run these from the worktree:

~~~bash
git rev-parse --show-toplevel
git rev-parse --path-format=absolute --git-common-dir
~~~

The first result is the worktree root. The parent of the second result is the main checkout because
the common Git directory is `<main-checkout>/.git`. Stop if the two roots are the same: this branch
is only for a linked worktree.

Confirm `<main-checkout>/.brain` and `<main-checkout>/.beads` exist before changing anything. Stop
on any existing worktree entry that is not already the intended symlink; never replace or merge a
real file or directory.

`<main-checkout>/.brain` and `<main-checkout>/.beads` are themselves symlinks into the Brainspace
(`~/dotbrain/brainspaces/<name>/.brain` and `.beads`). Resolve them to that real target now, rather
than linking to the main checkout's symlink directly:

~~~bash
readlink -f <main-checkout>/.brain
readlink -f <main-checkout>/.beads
~~~

Always link the worktree straight to this resolved Brainspace path, never to
`<main-checkout>/.brain` itself. A worktree link that targets another symlink creates a two-hop
chain; that chain resolves fine for `readlink -f`, `cat`, and `bd`, but breaks any tool with a
single-hop symlink-safety check (for example a check that guards against the link being swapped
mid-read) — the failure is silent until such a tool is used, so there is no local signal that the
chain is wrong.

## Create the links

On macOS or Linux (`<brainspace-brain>` / `<brainspace-beads>` are the paths `readlink -f` printed
above):

~~~bash
ln -s <brainspace-brain> <worktree>/.brain
ln -s <brainspace-beads> <worktree>/.beads
~~~

On Windows, use one of these native-symlink forms:

~~~bash
MSYS=winsymlinks:nativestrict ln -s <brainspace-brain> <worktree>/.brain
MSYS=winsymlinks:nativestrict ln -s <brainspace-beads> <worktree>/.beads
~~~

~~~cmd
mklink /D <worktree>\.brain <brainspace-brain>
mklink /D <worktree>\.beads <brainspace-beads>
~~~

Bare `ln -s` can silently copy directories on Windows. Always set
`MSYS=winsymlinks:nativestrict` in Git Bash or use `mklink /D`; if Windows refuses symlink creation,
enable Developer Mode or use an elevated shell.

## Link agent workspaces

The Brain and execution store are not the only wiring a worktree needs. Agent workspaces are real
directories whose skill and subagent links are gitignored, so a fresh worktree has none — no skills,
no subagents. Link the project's assets into the worktree from its Brainspace.

The project name is the Brainspace directory name (the parent of `<brainspace-brain>`). From the
worktree:

~~~bash
dotbrain skills link --scope project --project <name> --repo <worktree>
dotbrain agents link --scope project --project <name> --repo <worktree>
~~~

`--repo` is a reconcile target, not an attachment: it materializes `.claude` / `.codex` in the given
checkout and links the declared skills and subagents. It writes nothing in the Brainspace and never
creates a `.brain` / `.beads` link. Skip this step only when the project declares no agent
workspaces.

## Verify

Do not accept directory existence as proof. Verify both entries are symlinks and resolve directly to
the Brainspace, in one hop:

~~~bash
test -L <worktree>/.brain && readlink <worktree>/.brain
test -L <worktree>/.beads && readlink <worktree>/.beads
~~~

Each `readlink` result (not `readlink -f`) must already be the Brainspace path itself, matching
`<brainspace-brain>` / `<brainspace-beads>` above — not `<main-checkout>/.brain` or
`<main-checkout>/.beads`. If it names the main checkout, the link was made against the wrong target;
remove it and relink against the resolved Brainspace path.

On PowerShell, inspect `LinkType` and `Target`:

~~~powershell
Get-Item -Force <worktree>/.brain | Select-Object LinkType, Target
Get-Item -Force <worktree>/.beads | Select-Object LinkType, Target
~~~

Finish only when both are real symbolic links targeting the Brainspace directly (a single hop, not
a chain through the main checkout's own links). The worktree can then load `.brain/AGENTS.md` and
use `bd` against the shared execution store.

When the project declares agent workspaces, also confirm each one resolves the project's skills and
subagents — for example `<worktree>/.codex/agents` and `<worktree>/.claude/agents` hold symlinks for
the packaged roles, and `<worktree>/.claude/skills` holds the project's skills.
