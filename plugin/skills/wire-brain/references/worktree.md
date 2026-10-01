# Worktree attachment

Use the CLI to connect a linked Git worktree to its main checkout's existing Brainspace.
Git metadata supplies the main checkout; directory placement and worktree names do not supply
project identity. A missing or conflicting main-checkout relationship is an error to resolve
before attaching.

## Attach

From the worktree, run:

```bash
dotbrain wire
dotbrain doctor
```

From elsewhere, run `dotbrain wire --repo <worktree>`. The CLI creates direct `.brain` and enabled
`.beads` links into the shared Brainspace and real checkout-local runtime directories. It delivers
the selected skills and subagents, preserving project-owned workspace files. It keeps the
registered main-checkout path and project declarations unchanged.

On Windows, enable Developer Mode if directory symlink creation fails, then repeat the CLI
operation. Use the CLI's diagnostics rather than hand-creating links.

## Maintain or detach

```bash
dotbrain refresh
dotbrain skills link
dotbrain agents link
dotbrain unwire
```

Run these from the wired worktree. Refresh and asset linking target that checkout; refresh also
maintains the shared Brain conventions and tracker. Asset linking can explicitly target another
wired checkout with `--repo <worktree>`; any `--project` must match its wiring.

Detachment removes only this checkout's managed wiring and pointer. It preserves the shared
Brain and tracker, main-checkout registration, user-owned workspace content, and exclusion
entries still needed by another wired checkout. `--all` selects registered projects rather than
sweeping every worktree.

## Verify

- `dotbrain doctor` reports no relevant errors from the attached worktree.
- `.brain` resolves directly to the same Brainspace as the main checkout; enabled `.beads`
  resolves directly to its shared execution store.
- Runtime directories match the declared `agents:` selection. Skills and Claude agents are
  symlinks; Codex agents are marked real TOML files.
- `git rev-parse --git-path info/exclude` identifies the exclusion file holding managed entries.
- `git status --short` shows no unexpected tracked changes.
- Enabled Beads works with `bd ready`, including a valid empty tracker.
- Detachment leaves the main checkout and other wired worktrees usable.
