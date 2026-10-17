# Changelog

## [0.9.0](https://github.com/arminzou/dotbrain/compare/v0.8.0...v0.9.0) (2026-10-17)


### ⚠ BREAKING CHANGES

* **workflow:** `close-design` now runs only when invoked explicitly (`/dotbrain:close-design` in Claude Code); describing the job no longer triggers it. The lead agent now closes accepted reviews and approved work items itself after independent review; PR approval, merge, and release stay human-owned.

### Features

* **skills:** add `run-retro` for private retrospectives and public rule proposals ([5b1062d](https://github.com/arminzou/dotbrain/commit/5b1062d033fbba8a00bc6f16587b674aae199d1c))
* **workflow:** let agents finish approved work and add agent retrospectives ([5b1062d](https://github.com/arminzou/dotbrain/commit/5b1062d033fbba8a00bc6f16587b674aae199d1c))


### Bug Fixes

* **unwire:** warn when an edited pointer line is left in `AGENTS.md` or `CLAUDE.md` ([5b1062d](https://github.com/arminzou/dotbrain/commit/5b1062d033fbba8a00bc6f16587b674aae199d1c))

## [0.8.0](https://github.com/arminzou/dotbrain/compare/v0.7.0...v0.8.0) (2026-10-17)


### ⚠ BREAKING CHANGES

* **wire:** `dotbrain wire --no-repo` is removed, and `projects list/show --json` no longer reports `brain_only`; a null `checkout` means no registered checkout. Move a Brain-only project onto a repository (it may be private and docs-only) with `dotbrain wire --project <name>` from that repository, or archive the Brainspace by moving it out of `brainspaces/`.

### Features

* **wire:** require a repository as every project's working home ([1510bce](https://github.com/arminzou/dotbrain/commit/1510bcebb450c0127e2f1454324f8f3508253a5c))


### Bug Fixes

* **doctor:** drop the repeated path from the skip message ([0b588c6](https://github.com/arminzou/dotbrain/commit/0b588c65175d15a6a677ffce4bc5b188409f90b6))
* **doctor:** skip shared checkouts absent on this machine under --all ([5e604c6](https://github.com/arminzou/dotbrain/commit/5e604c64234e96078752104ac5b6603f503f3939))

## [0.7.0](https://github.com/arminzou/dotbrain/compare/v0.6.1...v0.7.0) (2026-10-15)


### Features

* **skills:** let a lead dispatch workers in another agent runtime ([5c58135](https://github.com/arminzou/dotbrain/commit/5c5813591fc4902c2140c033b3a01dbb9e9088fb))


### Bug Fixes

* **agents:** reduce Codex review overhead ([7b41af6](https://github.com/arminzou/dotbrain/commit/7b41af6e1105f5590257a8668cf91066f200893c))
* **docs:** restore link previews with the dark banner ([81971f8](https://github.com/arminzou/dotbrain/commit/81971f887aa23c8e160527a8a2f5e26c1da35e8e))
* **skills:** stop blocked on human-set settings and keep resume permissions ([cabd341](https://github.com/arminzou/dotbrain/commit/cabd3419aa1ce0e85ca87c1e00035efd477b99ff))


### Documentation

* **readme:** clarify private workspace and workflow ([5637d0d](https://github.com/arminzou/dotbrain/commit/5637d0d3b1c7f6381f1ce05a41ae4c4752285e66))
* **skills:** record qualified Claude Code CLI worker launch and resume ([16af898](https://github.com/arminzou/dotbrain/commit/16af898e4ec6de663097adaf4b6cc20605738f22))
