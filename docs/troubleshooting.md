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
3. **Codex:** trust the dotbrain hook in `/hooks`, then start a new thread.
4. Start a fresh session. The hook runs at session start, not mid-session.

### `.brain` or `.beads` is missing or dangling

::: code-group

```bash [Main checkout]
dotbrain refresh        # repair links in an already-wired repo
dotbrain wire           # or reconnect from scratch
```

```text [Git worktree]
Ask your agent: "run wire-brain to repair this worktree"
```

:::

A worktree uses the main checkout's Brain. `wire-brain` derives the main checkout from Git and
links only `.brain` and `.beads`. Do not create links under `.claude` or `.codex` by hand: their
targets are relative paths that the CLI computes.

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
`dotbrain update` prints the upgrade command for however the CLI was installed.

### `dotbrain site` fails

Check `node --version`; the site needs Node.js 22.12 or later. A build failure names the file and
line of the broken link or frontmatter. See [Brain site](brain-site.md#what-fails-the-build).

## FAQ

### Does anything from my Brain reach the code repo?

No. The repo holds gitignored links, and each link is ignored individually. The Brain and Beads
state live under `~/dotbrain`, which is its own Git repository.

### How do I use dotbrain on a second machine?

Clone your dotbrain home first, then install the plugin and CLI and wire each repo:

```bash
git clone <your-remote> ~/dotbrain
dotbrain bootstrap
dotbrain wire --repo ~/repos/my-app
```

For an issue tracker shared live across machines, use the
[server Beads backend](beads-backend.md#server-mode).

### Can I keep the Brain somewhere other than `~/dotbrain`?

Yes. Set `DOTBRAIN_HOME` to the directory you want.

### Can I use dotbrain without a code repo?

Yes. `dotbrain wire --no-repo --name <project>` creates a Brain-only Brainspace.

### How do I stop using dotbrain on a repo?

```bash
dotbrain unwire --dry-run   # preview
dotbrain unwire             # disconnect, keep the Brainspace
```

Add `--archive` to move the Brainspace aside or `--delete` to remove it. See
[Wiring](wiring.md#unwire).

### Which agents are supported?

Claude Code and Codex. Choose which workspaces a project gets with `agents:` in
[`project.yaml`](configuration.md#project-yaml).
