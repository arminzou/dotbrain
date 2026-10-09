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

## Failure recovery

If the GitHub release exists but PyPI publication fails, inspect the Release
workflow and PyPI before retrying. Rerun a failed job only when that version has
not been published. PyPI versions cannot be reused, and published tags must not
be moved. Fix a published defect in a new release.

`scripts/bump.py` remains available for exceptional manual version preparation;
it is not part of the automated release cycle.
