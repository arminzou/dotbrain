# Skills

The plugin delivers five workflow-independent core skills and needs no private
skill library. Select your own global skills in `~/dotbrain/config.yaml` and
project skills in `brainspaces/<name>/.brain/project.yaml`. These selections add
user resources without changing the packaged core inventory.

## Select and reconcile skills

Codex project skills are linked into `<checkout>/.agents/skills/`. Its configuration and
subagents remain under `.codex/`; global skills still use `~/.codex/skills/` and configured
profiles. Claude Code and the other runtimes keep their existing destinations.

`wire`, `refresh`, and `skills link` migrate legacy `.codex/skills/` links whose targets establish
Dotbrain ownership. A selected legacy link is removed only after its replacement is delivered;
stale owned links are pruned. Foreign or ambiguous files, directories, and links are preserved
and reported. Destination collisions keep the legacy link until you resolve the conflict and
rerun reconciliation. Each managed resource is ignored individually, and `unwire` removes owned
links from both locations. These delivery checks establish filesystem state; native runtime
discovery and invocation need separate verification.

Both scopes accept an individual skill or a bundle directory:

```yaml
# ~/dotbrain/brainspaces/my-app/.brain/project.yaml
skills:
  - my-collection/specific-skill
  - another-collection
```

```yaml
# ~/dotbrain/config.yaml
version: 4
profiles:
  claude-code: [~/.claude-work]
skills:
  - another-collection
```

Global linking uses each runtime's default home. For Claude Code and Codex, `profiles` adds
extra homes, each receiving skills in `<home>/skills`; missing homes are skipped. Use runtime
homes rather than folders inside project checkouts. See [configuration](configuration.md#global-skills).

A directory containing `SKILL.md` selects itself, even when it has descendant skills. Otherwise
dotbrain discovers descendant `SKILL.md` directories recursively, excluding `node_modules`.
Overlapping selections of the same source are deduplicated. Different sources mapping to the
same destination name, including case collisions on a case-insensitive filesystem, fail before
destination changes. Missing paths, non-directories, and empty bundles fail actionably.

```bash
dotbrain skills list                         # discover sources
dotbrain skills link                         # current wired checkout
dotbrain skills link --project my-app         # registered checkout
dotbrain skills link --scope global           # explicit global homes
dotbrain skills link --runtime codex           # declared Codex workspace only
```

Name skills or bundles after `link` to select and deliver them in one step, and use `unlink` to
deselect them and remove their links:

```bash
dotbrain skills link my-collection/specific-skill              # this checkout's project
dotbrain skills link another-collection --scope global          # every project
dotbrain skills unlink my-collection/specific-skill
```

These commands change only the scope's `skills:` list. Comments and the rest of the file stay as
they are. An entry that does not exist, a name collision, or a layout dotbrain cannot edit
exactly fails before the file changes; then edit the list by hand. Entries cannot be combined
with `--all`: global scope already reaches every project.

Adding or removing skills from a selected bundle takes effect on the next reconciliation; the
declaration stays unchanged. Removed owned links are pruned, while foreign entries are preserved.
`projects show`, catalogs, and doctor use the same expanded selection.

## Skills from external repositories {#external-repositories}

Your skill library is `~/dotbrain/skills`. An external skill repository joins it as a Git
submodule of the dotbrain home, so [home sync](session-context.md#home-sync) shares it with your
other machines by its commit:

```bash
dotbrain skills add https://github.com/backnotprop/pstack.git   # skills/pstack, committed
dotbrain skills link pstack/skills/how                          # select what you want
dotbrain skills update                                          # latest commit of every repository
dotbrain skills update pstack --ref v0.15.36                    # a tag, branch or commit, even older
dotbrain skills remove pstack                                   # deselect everywhere, remove, commit
```

- **`add`** clones the repository into `skills/<name>` (`--name` changes the folder, `--ref` pins
  a version), refuses one without any `SKILL.md`, commits it, and lists the `link` command for
  each skill it found. It selects nothing.
- **`update`** moves each repository to its remote's latest commit, or one repository to `--ref`,
  commits each move, and relinks every project and the global homes so new skills in a selected
  bundle appear and removed ones disappear.
- **`remove`** deselects the repository's skills in `config.yaml` and every `project.yaml`, removes
  the submodule and its cloned data, and commits all of it together, then relinks.

`update` skips, and `remove` refuses, a repository with uncommitted changes or unpushed commits.
Push or discard that work first.

Home sync keeps machines in step:

- **Other machines.** A full sync checks out each recorded commit and clones repositories that are
  missing. `dotbrain bootstrap` clones them too, so a fresh clone of the home gets its skills
  before the first session.
- **Changes made with Git.** A repository added with `git submodule add`, or moved forward with
  `git pull` inside it, is recorded by the next sync once that commit is on the repository's own
  remote. Another machine could not fetch a commit that exists only on yours. Sync never records
  an older commit, because that also describes a machine that has not caught up; use
  `dotbrain skills update --ref` to move back.
- **Local work is left alone.** A repository with uncommitted changes or unpushed commits is not
  recorded or moved. Sync reports it and still integrates everything else.

If two machines record different commits for the same repository, sync stops without merging
and reports it. Merge in `~/dotbrain`, check out the commit to keep in the submodule, `git add`
it, commit, and sync again. `dotbrain doctor` reports repositories that are not cloned, have
uncommitted changes, or are not at their recorded commit.

## Core capabilities {#core-workflow}

| Skill | Capability |
| --- | --- |
| `wire-brain` | Provision, attach, inspect, and repair Brainspaces and runtime resources |
| `brain-convention` | Explain shared workspace identity, resource ownership, records, and privacy |
| `maintain-brain` | Capture and maintain private vocabulary, decisions, designs, findings, and references |
| `work-graph` | Inspect and maintain native Beads records, dependencies, and ownership |
| `repo-rules` | Initialize and reconcile adopted repository requirements and assess enforcement |

All five allow model invocation for their stated operations. Engineering planning,
execution, review, and delivery belong to your selected workflow. Shared writing
and syntax references live under `maintain-brain/references/`.

## Convention {#optional-skills-invoked-by-name}

The session-start hook delivers the shared convention. Invoke `brain-convention`
when the hook did not run. In Claude Code use `/dotbrain:<name>`; in Codex select
the skill name exposed by the installed runtime.

## Custom subagents {#subagents}

The core ships no workflow agents. Operator-selected custom Claude Code and Codex
agents retain global and project delivery through `subagents:` in `config.yaml`
and `project.yaml`. Claude definitions use links; Codex definitions use generated
TOML copies. Customize the source in your private home. The `dotbrain-` namespace
stays reserved to protect preserved old resources from custom delivery.

## Installing them {#installing-them}

Claude Code and Codex load the core from their marketplace plugin. Hermes,
OpenCode, Pi, and Cursor retain their runtime-specific plugin and resource
delivery paths. See [getting started](getting-started.md) for installation and
[session context](session-context.md) for hook and discovery boundaries.

## Old resources and notebooks {#retrospectives}

Displaced workflow entrypoints, role composition, and the mandatory retrospective
process are removed. Existing `RETRO.md` notebooks, private sources, work records,
and history remain recoverable. Modified or ambiguous old resources are preserved
and reported. Read [upgrade guidance](upgrading.md) before updating a live setup.

## Optional engineering mode

The CLI delivers `dotbrain-pstack` only to explicitly opted-in projects; it is
not a sixth marketplace core skill. See [setup and qualification](workflow.md#pstack).
