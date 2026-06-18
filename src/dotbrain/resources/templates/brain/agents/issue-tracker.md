# Issue tracker conventions

Read at session start by `operate-execution` (private execution engine) and `triage-public`
(public tracker). Holds the **project-specific** conventions that span both layers; the generic
workflow lives in those skills. Record deviations and additions only — empty sections mean pure
defaults. Active tools are selected in `project.yaml` (`execution-engine:`, `public-tracker:`).

## Linking

Project conventions for linking public issues to private work items, beyond the skills' default
(the private item holds an external reference; a PR `Closes #N` closes only the public issue).

## Decisions

When a work item must pair with an ADR, and where those ADRs live. Default: none.

## Priority

Project priority conventions, including any public-severity to private-priority mapping. Default:
the engine's native priorities, unmapped.

## Labels

Public-label to native-field mappings, or a facet label vocabulary, live in `agents/labels.md`
(owned by `operate-execution`, created on demand). Absent means pure native fields.
