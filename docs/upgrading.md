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

The five core skills work with any engineering workflow. Select its skills like any other
skills; see [choosing a workflow](workflow.md#skill-workflow).

## Run output in scratch

Workflows now write each run's trails, plans, briefs, reports, evidence, and prototypes in
`.brain/scratch/<yyyy-mm-dd>-<slug>/`, and `docs/` holds maintained records only. Home sync never
commits a path under a Brain's `scratch/`. Add `brainspaces/*/.brain/scratch/` to the home
`.gitignore` as well, so other Git commands in the home skip it; `dotbrain doctor` warns until the
line is there.

Before moving existing run output, keep any private evidence that later work still needs in the
tracker or a maintained record. Files that home sync skipped for their size were never committed,
so a moved and deleted copy cannot be recovered. Then move run output already in a Brain, such as
dated logs, verification reports, and evidence folders under `docs/`, into a run folder under
`scratch/`. Home sync records the moved files as deleted; earlier commits keep them. Rewrite any
record that cites one of the moved paths so it states the conclusion instead. If an earlier release
committed files under `scratch/`, run `git rm -r --cached` on them in the dotbrain home and commit
at once: the next sync resets the index, so an uncommitted removal is undone. Other machines delete
their copies when they pull that commit, so back up anything you want to keep first.
`dotbrain doctor` lists any tracked scratch files that remain.

`wire` no longer creates a `.dotbrain-tmp/` exclude in checkouts. Move anything you still need out of
an existing `.dotbrain-tmp/` folder, then delete the folder; `unwire` removes its old exclude entry.
