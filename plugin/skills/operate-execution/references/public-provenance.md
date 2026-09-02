# Public provenance and PRs

Governs work that originates from, or lands through, the public issue tracker (`triage-public`).

## One-directional promotion

The link has one direction: promote an existing public issue inward by creating a private item that
references it. The public issue exists for reporter or contributor collaboration; the private item
exists for execution. A private bead, epic, or design never causes a public tracking issue to be
created. A PR may surface any change for review without a companion public issue.

When a PR closes an existing public issue, `Closes #N` closes only that issue; the private item
still needs an explicit close. Mechanics live in [beads.md](beads.md).

## PR body verification section

When a private item's work lands through a public PR, the PR body must carry a `Verification`
section restating the verification evidence in audience-safe, plain terms — no `.brain/` paths,
ADR numbers, or `design:` spec-ids. The private item may keep the full evidence in its own notes or
the linked design doc; the PR gets the public rendering only.

Landing here is local review by default because manual, turn-by-turn work is reviewed continuously.
Use a PR when the user wants a review surface or the work is already part of public collaboration;
do not create an issue merely to justify the PR.
