# Getting Started

Dotbrain ships as a plugin. Install it into your coding agent first, and the plugin's
`wire-brain` skill installs the CLI for you on first use. This guide walks that path in about five minutes:

1. Install the plugin.
2. Get the CLI.
3. Wire a repo.
4. Back up your dotbrain home.
5. Verify the result.

| You need | Notes |
| --- | --- |
| Claude Code or Codex | Either runtime, or both |
| Git | The dotbrain home is a Git repository |
| `uv` and `bd` (Beads) | Installed for you by the plugin's installer |
| Windows only: Developer Mode | Lets dotbrain create directory symlinks without Administrator |

## Before You Start

- You do not need a clone of this repo. The plugin carries its own installer.
- By convention, dotbrain keeps private project state under `~/dotbrain`
  (`%USERPROFILE%\dotbrain` on Windows). Set `DOTBRAIN_HOME` only to override it.
- The code repo you wire stays public or private on its own terms; dotbrain keeps Brain and
  execution state outside that repo.

::: warning Windows
Enable [Developer Mode](https://learn.microsoft.com/windows/apps/get-started/enable-your-device-for-development)
before wiring, so dotbrain can create directory symlinks without Administrator privileges.
:::

## 1. Install the Plugin

The Brain-coupled skills, the dotbrain convention, and the session-start hook are delivered as a
plugin, so each agent runtime installs them once per machine rather than per repo.

::: code-group

```text [Claude Code]
/plugin marketplace add arminzou/dotbrain
/plugin install dotbrain@dotbrain
```

```bash [Codex]
codex plugin marketplace add arminzou/dotbrain
codex plugin add dotbrain@dotbrain
```

:::

In Claude Code, send the two lines as separate prompts.

::: tip Codex needs one extra step
Codex does not run a plugin's hooks until you approve them: start `codex`, open `/hooks`, trust the
dotbrain hook, then start a new thread. Until then the skills load but Brain context is not injected
at session start. Claude Code runs the hook as soon as the plugin installs.
:::

Because the plugin installs at user scope, its skills are available in every session, including
repos that are not wired yet — which is how `wire-brain` is reachable before you have wired
anything.

### If `marketplace add` fails on Windows

Claude Code clones the marketplace into a staging directory and renames it, and on Windows that
rename can fail with `EBUSY` or `EPERM` while Defender or the Search Indexer still holds the
freshly written files
([claude-code#58241](https://github.com/anthropics/claude-code/issues/58241)). Retry once; the
lock window is short. If it keeps failing, clone the marketplace yourself:

```bash
git clone https://github.com/arminzou/dotbrain \
  ~/.claude/plugins/marketplaces/dotbrain
```

Then add an entry for it under `~/.claude/plugins/known_marketplaces.json` and restart Claude
Code, following the shape of the entries already there.

## 2. Get the CLI

The plugin delivers skills and Brain context; the `dotbrain` CLI does the wiring. They are
separate installs.

**Already have a dotbrain home?** If you have used dotbrain on another machine, your `~/dotbrain`
is a git repo holding every Brainspace. Clone it before anything else, so this machine picks up
your existing Brains instead of starting an empty one:

```bash
git clone <your-remote> ~/dotbrain
```

`wire-brain` asks about this when it finds no dotbrain home, but cloning first saves the round
trip.

**Let your agent do it.** Ask it to wire the repo, or invoke `wire-brain` directly. The skill
checks whether `dotbrain` is on `PATH` and, if it is missing, runs the installer shipped inside
the plugin — which provides `uv`, `bd` (Beads), the CLI version pinned to this plugin release, and
then runs `dotbrain bootstrap`.

**Or install it yourself from PyPI.** Requires `uv` or `pipx` already on your machine:

::: code-group

```bash [uv]
uv tool install dotbrain
```

```bash [pipx]
pipx install dotbrain
```

:::

This installs the CLI only — it does not install `bd`
(Beads), which `dotbrain` shells out to for issue tracking. Run `dotbrain bootstrap` afterward,
then `dotbrain doctor --all` to check machine readiness before wiring a project. Install `bd`
1.3.1 or later yourself from [the Beads repo](https://github.com/gastownhall/beads) before wiring a
project with a tracker. Doctor checks tracker readiness once a project has a tracker configured.

**Or run the plugin's installer by hand.** It provisions `uv` and `bd` for you if either is
missing, then installs the CLI — no prerequisites needed, from the runtime's plugin cache:

::: code-group

```bash [macOS / Linux]
~/.claude/plugins/cache/dotbrain/dotbrain/*/scripts/install.sh
```

```powershell [Windows]
pwsh -NoProfile -File "$env:USERPROFILE\.claude\plugins\cache\dotbrain\dotbrain\*\scripts\install.ps1"
```

:::

Either script installs `uv` and `bd` if they are missing, installs the pinned CLI, and runs
`dotbrain bootstrap` — which seeds your global dotbrain home with configuration and delivers
selected global skills and subagents. The plugin supplies the session-start hook. Running the
installer a second time is safe.

::: warning
Keep the CLI and the plugin on the same version. The plugin's installer pins a matching CLI tag,
so the two stay aligned as long as you let it do the install.
:::

## 3. Wire a Repo

From the code repo you want to wire:

```bash
cd ~/repos/my-app
dotbrain wire
```

Or from anywhere, with `dotbrain wire --repo ~/repos/my-app`.

Wiring creates or repairs a private Brainspace for that project and connects the repo to it through
gitignored links. Your repo gains:

```mermaid
treeView-beta
  accTitle: What wiring adds to a code repo
  ~/repos/my-app/
    .brain ## link to the Brainspace's .brain/
    .beads ## link to the Brainspace's .beads/
    .claude/ ## skill and subagent links, individually ignored
    .codex/ ## skill links and generated agent files, individually ignored
```

[Wiring](wiring.md) explains each entry.

## 4. Back Up Your Dotbrain Home

`dotbrain bootstrap` makes `~/dotbrain` a Git repository, but it never adds a remote. Until you add
one, every Brain exists on one disk only. Create an empty **private** repository on GitHub, GitLab,
or your own Git server, then push to it:

```bash
cd ~/dotbrain
git status
git add .
git commit -m "Back up dotbrain home"
git remote add origin <private-remote-url>
git push -u origin HEAD
```

Review the files before staging; keep credentials out of Git. Bootstrap initializes the repository
without creating a commit, so the first push needs the commit above. For later Brain changes,
stage and commit the changes you want to keep, then push. The remote is also how a second machine gets your Brains:
[clone it there](#_2-get-the-cli) before wiring anything.

::: danger Keep the remote private
The remote holds every project's Brain, including its decisions and designs. A public remote
publishes all of it.
:::

::: warning The remote does not hold your issues
The Beads tracker's database is ignored by `~/dotbrain/.gitignore`, so pushing backs up the Brain
but not the issues. To back up or share the issues too, give the project a Dolt remote
(`beads.remote`) or use a shared server. See [Beads backend](beads-backend.md).
:::

## 5. Verify the Result

For a read-only health check:

```bash
dotbrain doctor
```

To repair generated wiring after a config or plugin change:

```bash
dotbrain refresh
```

At this point you should have:

- a seeded `~/dotbrain/config.yaml`
- a project Brainspace under `~/dotbrain/brainspaces/<name>/`
- local wiring in the repo that points at that Brainspace
- Brain context injected at the start of your next agent session

Start a fresh session in the wired repo to confirm the last one. The agent should already know
the project's vocabulary and standing decisions without being told.

## Staying Current

When a new dotbrain release lands, update the plugin and the CLI together.

::: code-group

```text [Claude Code]
/plugin            # update dotbrain from the menu
/reload-plugins
```

```bash [Codex]
codex plugin marketplace upgrade
codex plugin add dotbrain@dotbrain
```

:::

Then refresh the CLI to match, either by asking your agent or by re-running the install command
from step 2 with the new tag.

To update only the released CLI, upgrade it with the tool that installed it:

::: code-group

```bash [uv]
uv tool install dotbrain@latest
```

```bash [pipx]
pipx upgrade dotbrain
```

```bash [pip]
python -m pip install --upgrade dotbrain
```

:::

With uv, use `dotbrain@latest` rather than `uv tool upgrade dotbrain`: an install pinned to one
version, such as the plugin installer's, stays on that version under `uv tool upgrade`.

Updating the CLI does not update plugins or private dotbrain data. Contributor checkouts remain
editable: update the checkout with Git instead.

After updating the matching plugin and CLI, run `dotbrain bootstrap` for machine resources and
`dotbrain refresh --all` for registered projects. To roll back the code, restore the previous CLI
and its matching plugin; review generated convention changes before maintaining projects with it.

### CLI migration

The CLI uses one selection vocabulary. Retired invocations fail rather than acting as aliases;
update existing scripts using this table.

| Previous invocation | Current invocation |
| --- | --- |
| `--name <name>` | `--project <name>` |
| `--dotbrain <path>` | `--home <path>` |
| `--target claude-code` | `--runtime claude` |
| `--target codex` or `--target all` | `--runtime codex` or `--runtime all` |
| `beads load` | `beads sync` |
| `wire --all` | `refresh --all` |
| `--beads-server-host`, `--beads-server-port`, `--beads-server-user` | `--server-host`, `--server-port`, `--server-user` |
| `--beads-ssh-host`, `--beads-database`, `--beads-remote` | `--ssh-host`, `--database`, `--remote` |
| Asset linking with implicit global scope | `skills link --scope global` or `agents link --scope global` |
| `update` | Upgrade with the package manager that installed the CLI |
| `unwire --all` | `unwire --project <name>` per project |
| Unwire archival, deletion, or preview flags | `unwire` detaches; manage retained directories through filesystem actions |

Hidden command aliases are removed. Bare project commands now target the current wired checkout;
outside it, select `--project`. Existing configuration keys such as `targets.claude-code` keep
their spelling. Skills and Claude agents remain symlinks; agent reconciliation migrates owned
Codex agent symlinks into marked real files and preserves foreign entries.

JSON finding severity `advisory` is now `warning`, matching the existing warning results.
Update scripts that match the old value; it is no longer emitted. Other result fields and exit
codes are unchanged, and warnings alone still exit successfully. See [CLI Reference](cli-reference.md).

## Edit Config Only When Needed

Most first-time setups can leave the default embedded beads mode alone.

When you do need configuration:

- [Configuration](configuration.md) covers `config.yaml` and `project.yaml`.
- [Skills](skills.md) covers skill selection.

## Next

- [The workflow](workflow.md) shows how the skills carry work from idea to closed design.
- [Architecture](architecture.md) explains the Brainspace model.
- [Troubleshooting & FAQ](troubleshooting.md) covers common setup problems.
