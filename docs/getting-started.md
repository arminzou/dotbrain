# Getting Started

Dotbrain ships as a plugin. Install it into your coding agent first, and the plugin's
`wire-brain` skill installs the CLI for you on first use. This guide walks that path:

1. Install the plugin into Claude Code or Codex.
2. Get the `dotbrain` CLI (your agent does this, or you do it by hand).
3. Wire one code repo to a private Brainspace.
4. Verify the wiring.

## Before You Start

- You do not need a clone of this repo. The plugin carries its own installer.
- By convention, dotbrain keeps private project state under `~/dotbrain`
  (`%USERPROFILE%\dotbrain` on Windows). Set `DOTBRAIN_HOME` only to override it.
- The code repo you wire stays public or private on its own terms; dotbrain keeps Brain and
  execution state outside that repo.
- **On Windows**, enable
  [Developer Mode](https://learn.microsoft.com/windows/apps/get-started/enable-your-device-for-development)
  before wiring, so dotbrain can create directory symlinks without Administrator privileges.

## 1. Install the Plugin

The Brain-coupled skills, the dotbrain convention, and the session-start hook are delivered as a
plugin, so each agent runtime installs them once per machine rather than per repo.

Claude Code — send these as two separate prompts:

```
/plugin marketplace add arminzou/dotbrain
```

```
/plugin install dotbrain@dotbrain
```

Codex:

```bash
codex plugin marketplace add arminzou/dotbrain
codex plugin add dotbrain@dotbrain
```

**Codex needs one extra step.** It does not run a plugin's lifecycle hooks until you approve
them: start `codex`, open `/hooks`, review and trust the dotbrain hook, then start a new thread.
Until you do, the plugin's skills load but Brain context is not injected at session start. Claude
Code runs the hook as soon as the plugin installs.

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

**Let your agent do it.** Ask it to wire the repo, or invoke `wire-brain` directly. The skill
checks whether `dotbrain` is on `PATH` and, if it is missing, runs the installer shipped inside
the plugin — which provides `uv`, `bd` (Beads), the CLI version pinned to this plugin release, and
then runs `dotbrain bootstrap`.

**Or install it by hand.** Run the same installer the plugin ships, from the runtime's plugin
cache:

```bash
# macOS and Linux
~/.claude/plugins/cache/dotbrain/dotbrain/*/scripts/install.sh
```

```powershell
# Windows
pwsh -NoProfile -File "$env:USERPROFILE\.claude\plugins\cache\dotbrain\dotbrain\*\scripts\install.ps1"
```

Either script installs `uv` and `bd` if they are missing, installs the pinned CLI, and runs
`dotbrain bootstrap` — which seeds your global dotbrain home with `config.yaml`, global agent
hooks, and global skill links. Running it a second time is safe.

Keep the CLI and the plugin on the same version. The plugin's installer pins a matching CLI tag,
so the two stay aligned as long as you let it do the install.

## 3. Wire a Repo

Move to the code repo you want to wire and run:

```bash
dotbrain wire <repo>
```

Example:

```bash
dotbrain wire ~/repos/projects/my-app
```

Wiring creates or repairs a private Brainspace for that project and connects the repo to it
through gitignored local links such as `.brain`, `.beads`, `.claude`, and `.codex`.

## 4. Verify the Result

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

Claude Code — run `/plugin`, update dotbrain from the menu, then:

```
/reload-plugins
```

Codex:

```bash
codex plugin marketplace upgrade
codex plugin add dotbrain@dotbrain
```

Then refresh the CLI to match, either by asking your agent or by re-running the install command
from step 2 with the new tag.

## Edit Config Only When Needed

Most first-time setups can leave the default embedded beads mode alone.

When you do need configuration:

- use [configuration.md](configuration.md) for `config.yaml` and `project.yaml`
- use [skills.md](skills.md) for skill layering

## Next

- [architecture.md](architecture.md) explains the Brainspace model.
- [cli-reference.md](cli-reference.md) lists the public commands.
