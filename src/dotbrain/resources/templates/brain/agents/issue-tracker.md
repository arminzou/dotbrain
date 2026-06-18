# Issue Tracker

Read by `operate-execution` and `triage-public` at session start. Declares project conventions for
both private execution and public intake. See `project.yaml` for which tools are active.

## Linking

- Public issues feed the private engine — they do not replace it.
- Inward: create a private work item and link it with `--external-ref <tracker>-<N>` when a public
  issue is accepted for execution.
- Outward: derive a public-safe description when promoting private work; update the private work
  item with the public reference once created.
- A PR `Closes #N` closes the public issue only. Close the private work item explicitly.

## Project conventions

(Record project-specific deviations and additions here. Empty means pure defaults — do not
restate the generic workflow above.)
