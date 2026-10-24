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

`uat/` holds an opt-in suite that checks, in disposable sandboxes, what agent runtimes actually
load from dotbrain: packaged and selected skills, the convention before the first request, one
hook call per event, and home sync that does not block on an unreachable remote. CI and plain
`uv run pytest` never run it, and it makes paid model calls.

Run it before a release PR that touches runtime delivery, the hooks, or a runtime adapter
(`plugin/`), and after upgrading a runtime it covers:

```bash
uv run --group uat pytest uat
```

Each journey runs on two backends. The host backend runs on native Windows with the runtime
installed. The container backend needs Docker running and builds `uat/Dockerfile` (Linux, with a
pinned runtime version and dotbrain from the checkout under test) once per checkout state; the
first build downloads base images and packages, and later runs reuse it. Without Docker, the
container journeys skip. Both backends need `uv` and these variables:

| Runtime | Variables |
| --- | --- |
| OpenCode | `UAT_OPENCODE_MODEL` as `<provider>/<model>`, and the provider's key: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, or `OPENROUTER_API_KEY` |
| Pi | `UAT_PI_MODEL` as `<provider>/<model>`, and the provider's key: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, or `OPENROUTER_API_KEY` |
| Cursor | `CURSOR_API_KEY` or `CURSOR_AUTH_TOKEN`; the account's default model answers. The host backend runs the CLI from its installer's location, `%LOCALAPPDATA%\cursor-agent` |

Only that key is passed, and only to the runtime process; a journey fails if it finds the key in
any sandbox file. A journey whose runtime or variables are missing skips and names what to set.

Each journey fingerprints the live runtime config and the live data root before and after, and
fails if they changed. Quit the runtime and other agent sessions on the machine first: their own
writes and home sync would fail the run.

Results, stamped with runtime version, OS, dotbrain revision, and for the container backend the
image digest, print at the end of the run and are written to `uat/results.json`. Cite them in the
release PR.

## Failure recovery

If the GitHub release exists but PyPI publication fails, inspect the Release
workflow and PyPI before retrying. Rerun a failed job only when that version has
not been published. PyPI versions cannot be reused, and published tags must not
be moved. Fix a published defect in a new release.

`scripts/bump.py` remains available for exceptional manual version preparation;
it is not part of the automated release cycle.
