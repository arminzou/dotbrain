# Releases

Release Please maintains a release PR against `main` from Conventional Commits.
Review its version and changelog before merging. Merging that PR authorizes Release
Please to create the tag and GitHub release; the tag triggers trusted publishing to PyPI.
The release is complete only when the Release workflow's publication step succeeds.

## Repository setup

Install a GitHub App on this repository with Contents, Pull requests, and Issues
read/write permissions. Keep its identity separate from the human reviewer.
Set the repository variable `RELEASE_PLEASE_APP_ID` to the App ID and the Actions
secret `RELEASE_PLEASE_PRIVATE_KEY` to its private key. Use an App token so generated
PRs and tags trigger CI and publishing. A `GITHUB_TOKEN`-created tag does not trigger
the tag workflow.

Keep the reviewed-PR rule on `main` and the existing PyPI trusted publisher for
`.github/workflows/release.yml`. After setup, run the release-please workflow manually
or push a releasable Conventional Commit (`fix` or `feat`) to `main` to start a cycle.

## Version updates

The Python strategy updates `pyproject.toml` and `src/dotbrain/__init__.py`.
Extra-file updaters handle both plugin manifests, annotated installer pins, and
the local Dotbrain package in `uv.lock`. Preserve the installers' inline
`x-release-please-version` comments. The lockfile selector uses `name.value`
because Release Please's TOML parser wraps scalar values; verify this selector
when upgrading the action. CI checks that all seven version values agree.

The manifest starts at the published `0.6.1` release. Do not advance it by hand
each cycle. Before 1.0, breaking changes bump the minor version. Use Conventional
Commit PR titles so squash merges contribute accurate versions and release notes.

## Runtime delivery UAT

`uat/` holds an opt-in suite that checks, in a Linux container, what the real agent runtimes and
their plugin tools do with what dotbrain installs. It needs Docker and `uv`, uses no API keys or
logins, and makes no model calls. For each of the six runtimes (Claude Code, Codex, OpenCode, Pi,
Cursor, Hermes) in a fresh container, it checks that:

- the clean install works: `dotbrain bootstrap`, `wire` and `refresh` deliver, and the Claude Code
  and Codex plugins install from a local marketplace;
- the runtime's own no-model listing commands show the delivered skills, the four `dotbrain-<role>`
  subagents and the plugin and hooks, where the runtime has such a command;
- the session-start and session-end commands, read from the runtime's delivered config and run as
  configured, print the convention whole, return within the runtime's hook limit with an unreachable
  remote, and leave the data root with a local commit ahead of its upstream.

Anything plain pytest already proves stays in `tests/`. CI and plain `uv run pytest` never run the
suite. Run it before a release PR that touches runtime delivery, the hooks, or a runtime adapter
(`plugin/`), and after upgrading a pinned runtime:

```bash
uv run --group uat pytest -n 4 uat
```

The first run builds `uat/Dockerfile` (pinned runtime versions, dotbrain from the checkout under
test) and downloads packages; later runs on the same checkout state reuse the image. Without Docker
the journeys skip. A runtime whose install fails in the image skips with the install error.

What each runtime's journey shows (the table is `uat/evidence.py`):

| Runtime | Evidence |
| --- | --- |
| Claude Code | install; plugin and its hooks (`claude plugin list`, `details`); project subagents and skills (`claude -p /context`); hook command |
| Codex | install; skills (`codex debug prompt-input`); plugin installed and enabled (`codex plugin list`); hook command. The checkout's `.codex/agents` are not listed by any command |
| OpenCode | install; skills with locations (`opencode debug skill`); plugin file in the resolved config (`opencode debug config`); hook command. No dotbrain agents are delivered |
| Hermes | install; plugin enabled (`hermes plugins list`); hook command. Skills are not listed |
| Pi | install and hook command only |
| Cursor | install and hook command only; every listing needs a login |

Accepted gaps: the suite never fires a runtime's hook through the runtime, so when a runtime calls
the hook is not covered; and it does not run on native Windows.

Results, stamped with runtime version, image digest, OS and dotbrain revision, print at the end of
the run and are written to `uat/results.json`. Cite them in the release PR.

## Failure recovery

If the GitHub release exists but PyPI publication fails, inspect the Release
workflow and PyPI before retrying. Rerun a failed job only when that version has
not been published. PyPI versions cannot be reused, and published tags must not
be moved. Fix a published defect in a new release.

`scripts/bump.py` remains available for exceptional manual version preparation;
it is not part of the automated release cycle.
