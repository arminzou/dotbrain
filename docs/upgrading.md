# Upgrading to the five-skill core

This breaking release ships `wire-brain`, `brain-convention`, `maintain-brain`,
`work-graph`, and `repo-rules`. Engineering workflow procedures and packaged
workflow agents have been removed. Keep the preceding release if those workflows
are still required. Existing private context, notebooks, Beads records, and user
skill and custom-agent sources remain yours.

Before changing a live installation, finish or safely hand off active writers.
Record actual candidates, claims, pending work, evidence and remaining limits;
upgrading does not accept work, close tasks, or renew allowances. Back up private
Brain/home files through their private Git history and backup, and back up Beads
through its Dolt remote or server backup. Home sync does not back up the tracker. Save configuration and delivered resources needed for
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


## Workflow selection

The five core skills work without pstack. The optional `dotbrain-pstack` mode
requires a separately prepared clean external source checkout and explicit
project `pstack.enabled` / `pstack.source` settings. It is delivered by the CLI,
not as a sixth marketplace skill. Follow [setup and qualification scope](workflow.md#pstack).
The initial native qualification targets are local Windows Claude Code and Codex;
source identity and generated resources are structural evidence, not a native pass.
Observed results belong to the exact release or PR verification record.

Mode links and `.dotbrain-pstack.json` are generated and ignored. Change project
selection, refresh each checkout, inspect preserved-resource notices, and start
fresh sessions. Modified caches, discovery records or foreign resources are
preserved rather than silently replaced or deleted. Keep the external dependency
pinned unless separately reviewing and qualifying its upgrade.
