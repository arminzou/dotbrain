---
name: wire-worktree
description: Wire a Git worktree that has no .brain or .beads by linking both back to the main checkout. Use when an agent starts inside a dotbrain project worktree without Brain context, especially before invoking other brain-coupled skills.
---

# Wire Worktree

Restore a linked Git worktree's access to the main checkout's Brain and execution store. This is a
worktree-local repair: do not run `dotbrain wire`, create a Brainspace, or copy either directory.

## Locate Both Checkouts

Run these from the worktree:

```bash
git rev-parse --show-toplevel
git rev-parse --path-format=absolute --git-common-dir
```

The first result is the worktree root. The parent of the second result is the main checkout because
the common Git directory is `<main-checkout>/.git`. Stop if the two roots are the same: this skill
is only for a linked worktree.

Confirm `<main-checkout>/.brain` and `<main-checkout>/.beads` exist before changing anything. Stop
on any existing worktree entry that is not already the intended symlink; never replace or merge a
real file or directory.

## Create The Links

On macOS or Linux:

```bash
ln -s <main-checkout>/.brain <worktree>/.brain
ln -s <main-checkout>/.beads <worktree>/.beads
```

On Windows, use one of these native-symlink forms:

```bash
MSYS=winsymlinks:nativestrict ln -s <main-checkout>/.brain <worktree>/.brain
MSYS=winsymlinks:nativestrict ln -s <main-checkout>/.beads <worktree>/.beads
```

```cmd
mklink /D <worktree>\.brain <main-checkout>\.brain
mklink /D <worktree>\.beads <main-checkout>\.beads
```

Bare `ln -s` can silently copy directories on Windows. Always set
`MSYS=winsymlinks:nativestrict` in Git Bash or use `mklink /D`; if Windows refuses symlink creation,
enable Developer Mode or use an elevated shell.

## Verify

Do not accept directory existence as proof. Verify both entries are symlinks and resolve back to
the main checkout:

```bash
test -L <worktree>/.brain && readlink <worktree>/.brain
test -L <worktree>/.beads && readlink <worktree>/.beads
```

On PowerShell, inspect `LinkType` and `Target`:

```powershell
Get-Item -Force <worktree>/.brain | Select-Object LinkType, Target
Get-Item -Force <worktree>/.beads | Select-Object LinkType, Target
```

Finish only when both are real symbolic links targeting the matching entries in the Git-derived
main checkout. The worktree can then load `.brain/AGENTS.md` and use `bd` against the shared
execution store.
