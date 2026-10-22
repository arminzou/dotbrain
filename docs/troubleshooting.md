# Troubleshooting & FAQ

Start every investigation with the read-only health check. It reports machine readiness, project
wiring, and Beads state drift without changing anything:

```bash
dotbrain doctor
```

## Common Problems

### The agent does not know the project

The session started without the dotbrain convention.

1. Confirm the repo is wired: `.brain` should exist at the repo root and resolve to a directory.
2. Confirm the CLI is on `PATH` for the agent's shell: `dotbrain --version`. The hook stays silent
   when it cannot find `dotbrain`.
3. **Codex:** trust the dotbrain hooks in `/hooks`, then start a new thread.
4. Start a fresh session. The hook runs at session start, not mid-session.

### `.brain` or `.beads` is missing or dangling

::: code-group

```bash [Main checkout]
dotbrain refresh        # repair links in an already-wired repo
dotbrain wire           # or reconnect from scratch
```

```bash [Git worktree]
dotbrain wire           # attach through the main checkout's existing wiring
dotbrain refresh        # maintain the current wired worktree
```

:::

A worktree uses the main checkout's Brain. The CLI finds that checkout through Git metadata and
delivers local runtime resources. Use the CLI to reconcile resources in `.claude` and `.codex`.

### Symlink creation fails on Windows

Enable [Developer Mode](https://learn.microsoft.com/windows/apps/get-started/enable-your-device-for-development),
which lets a normal user create directory symlinks, then run `dotbrain wire` again.

### `marketplace add` fails with `EBUSY` or `EPERM` on Windows

Defender or the Search Indexer is holding the freshly cloned files. Retry once. If it keeps
failing, follow the [manual clone steps](getting-started.md#if-marketplace-add-fails-on-windows).

### `bd: command not found`

`uv tool install dotbrain` installs the CLI only. Install Beads from
[its repository](https://github.com/gastownhall/beads), or run the plugin's installer, which
provisions both.

### The plugin and CLI versions disagree

Update both together, as described in [Staying current](getting-started.md#staying-current).
Use the upgrade command for the package manager that installed the CLI.

### `dotbrain site` fails

Check `node --version`; the site needs Node.js 22.12 or later. Follow the build error to the named
file and line: missing links, invalid frontmatter, and malformed HTML or Vue markup can fail a
build. For "Element is missing end tag", look for bare placeholders such as `<name>` or `<path>`
and wrap them in inline code, including in tables. See
[Brain site configuration](brain-site-configuration.md#what-fails-the-build).

## Home Sync

`dotbrain doctor` reports [home sync](session-context.md#home-sync) state from local Git data. It
does not fetch or change anything.

### Home sync left a conflict copy

Doctor reports `home sync: open conflict copy <path>`.

Both machines changed the same part of a file before either synced. Sync kept both versions:

- This machine's version stays in place under the original name.
- The other machine's version is saved beside it as
  `<stem>.sync-conflict-<date>-<host>` plus the original extension, for example
  `CONTEXT.sync-conflict-2026-10-20-LAPTOP.md`, where the host is the machine that merged and wrote the copy, not the
  machine whose version it holds.
  A second conflict on the same file and day adds a number, such as `-2`.

Sync never merges these for you. Open both files, merge what you want to keep into the original,
and delete the copy. The next sync records both changes, and the copy disappears on the other
machine too. The Brain site skips conflict copies, so they never show up as extra pages.

### A file stays uncommitted

Doctor reports `home sync: <path> is over the size limit and stays uncommitted`.

Sync never commits a file larger than `sync.max-file-size` (default 1 MB). Pick one:

- Commit it yourself in `~/dotbrain`, if it belongs there.
- Add it to `~/dotbrain/.gitignore`.
- Raise the limit in [`config.yaml`](configuration.md#sync).

`dotbrain sync` also warns about nested Git repositories inside the home. Sync never records them.

### Incoming changes touch an uncommitted file

`dotbrain sync` fails with `did not integrate <upstream>; nothing was pushed` followed by Git's
diagnostic.

The other machine changed or added a file whose incoming contents would overwrite an uncommitted
or ignored local file. This can include files over the size limit and nested Git repositories.
Git refuses the merge, leaves your local files as they were, and sync pushes nothing. Read Git's
diagnostic for the affected paths, resolve each one, then run `dotbrain sync`:

- Commit it yourself in `~/dotbrain`, or raise the limit, so sync can merge it.
- Move your local copy out of the home.
- Discard your local copy with `git restore <path>`, or delete it if it is untracked.

### Home sync is blocked

Doctor reports `home sync blocked: <state> in the dotbrain home`, and `dotbrain sync` fails.

Sync refuses to record while the home has a merge, rebase, cherry-pick, or revert in progress, has
unmerged paths, or is on a detached HEAD. Recording then would commit conflict markers or commit to
no branch. Finish or abort that operation with Git in `~/dotbrain`, check out the branch, and run
`dotbrain sync`. Until then, the hooks record nothing.
Sync leaves a merge you started yourself in place; it never aborts it for you.

### Commits are waiting to be pushed

Doctor reports `home sync: <n> local commits waiting to be pushed to <upstream>`.

The last push did not reach the remote. Either the machine was offline, or the remote moved: a full
sync gives up after four push attempts (the first try and three retries), and the push after an
agent turn, which never fetches, leaves its commits for the next full sync. The commits are safe.
The next sync pushes them, or run `dotbrain sync` now.
If it keeps failing, check that `git push` works by hand in `~/dotbrain`.

`home sync: no remote configured; sync commits stay local` means the home's branch has no upstream.
Add a private remote and set it, as in [Getting started](getting-started.md#_4-back-up-and-sync-your-dotbrain-home).

### Turn home sync off

Set `enabled: false` under `sync:` in `~/dotbrain/config.yaml`:

```yaml
# ~/dotbrain/config.yaml
sync:
  enabled: false
```

The hooks and `dotbrain sync` then do nothing, and doctor reports `home sync disabled`. Commit and
push the home yourself. `config.yaml` is shared through the remote: once you push this change,
each other machine turns sync off when its next sync brings the change in. Sync commits are ordinary commits, so nothing needs undoing.

## FAQ

### Does anything from my Brain reach the code repo?

The Brain stays private. The repo holds gitignored links and generated Codex agent definitions,
each ignored individually. The Brain and Beads
state live under `~/dotbrain`, which is its own Git repository.

### How do I use dotbrain on a second machine?

Clone your dotbrain home first, then install the plugin and CLI and wire each repo:

```bash
git clone <your-remote> ~/dotbrain
dotbrain bootstrap
dotbrain wire --repo ~/repos/my-app
```

After that, [home sync](session-context.md#home-sync) keeps the Brains current on both machines.
For an issue tracker shared live across machines, use the
[server Beads backend](beads-backend.md#server-mode).

### Can I keep the Brain somewhere other than `~/dotbrain`?

Yes. Set `DOTBRAIN_HOME` to the directory you want.

### Can I use dotbrain without a code repo?

Not anymore. Every project needs a repository as its working home, but it can be a private
repository that holds only documents. To move an older Brain-only project onto one, run
`dotbrain wire --project <project>` from that repository.

### How do I stop using dotbrain on a repo?

```bash
dotbrain unwire             # disconnect, keep the Brainspace
```

Archive or delete the retained Brainspace through your own filesystem workflow. See
[Wiring](wiring.md#unwire).

### Which agents are supported?

Claude Code and Codex, and Hermes on Linux only (see [Hermes on Linux](getting-started.md#hermes)).
Choose which workspaces a project gets with `agents:` in
[`project.yaml`](configuration.md#project-yaml).
