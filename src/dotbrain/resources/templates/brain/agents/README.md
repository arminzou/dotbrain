# agents/

Per-project agent operating conventions the agent reads while working.

- `issue-tracker.md` — conventions shared by `operate-execution` and `triage-public`, read by both
  at session start: linking, decisions/ADR policy, priority. Empty sections mean pure defaults.
- `labels.md` — public-label to native-field mappings, or a facet label vocabulary, owned by
  `operate-execution`. Created on demand; absent means pure native fields.

CLI mechanics for a specific engine or tracker (e.g. `bd`, `gh`) are *not* kept here — they ship
with the owning skill and are selected via `project.yaml` (`execution-engine:`, `public-tracker:`).
Skill *selection* is likewise not configured here; per-project skills live in `project.yaml` under
`skills:`.

See `DOTBRAIN.md` for the read order and operating rules.
