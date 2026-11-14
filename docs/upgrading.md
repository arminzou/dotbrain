# Upgrading to the five-skill core

This breaking release ships `wire-brain`, `brain-convention`, `maintain-brain`,
`work-graph`, and `repo-rules`. Engineering workflow procedures and packaged
workflow agents have been removed. Keep the preceding release if those workflows
are still required. Existing private context, notebooks, Beads records, and user
skill and custom-agent sources remain yours.

Before changing a live installation, establish a safe boundary for active writers
and back up private files and the Beads backend through their respective
persistence mechanisms. Save configuration and delivered resources needed for
rollback. Update matching CLI and plugin versions, then inspect `dotbrain doctor`
and `dotbrain refresh` results in a fresh session.

Project declarations named `packaged-subagents`, `retro`, `execution-engine`,
`public-tracker`, and `public-tracker-id` are obsolete. Refresh reports these keys
and leaves the declaration unchanged. Review and remove them explicitly while
preserving unrelated settings. Use `subagents` only for selected custom-agent
sources; unprefixed names such as `reviewer` now refer to your own source file.

Refresh removes old packaged agents only when their complete content matches a
known generated definition. Modified files, unknown `dotbrain-*` files, and
ambiguous links stay in place with an inspection notice. Inspect these preserved
resources and remove or relocate them explicitly before starting a session that
could discover them. Existing `RETRO.md` notebooks remain untouched; the core no
longer requires retrospective retrieval, curation, or writing.

Modified shared convention files are copied under the Brain's
`.dotbrain-preserved/` before the packaged convention replaces them; wire and
refresh report the saved path. Modified old runtime bundles are moved to
`.dotbrain-preserved/` outside the adapter's discovery directories. Inspect these
copies as private data. Ambiguous legacy skill caches are retained with a notice,
while obsolete managed delivery links are pruned.

Rollback restores the previous release and captured configuration and resources.
Reconcile work recorded after upgrading before restoring older private or backend
state. Rolling back software must not overwrite newer work records.
