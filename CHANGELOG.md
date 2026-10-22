# Changelog

## [0.12.0](https://github.com/arminzou/dotbrain/compare/v0.11.0...v0.12.0) (2026-10-22)


### Features

* **skills:** define lead completion handling for worker results ([0060c98](https://github.com/arminzou/dotbrain/commit/0060c98f25906c7229c8a9340bee6e4b3fe473cb))


### Bug Fixes

* **hooks:** label sync hooks and respect Codex timeout limit ([ff67d82](https://github.com/arminzou/dotbrain/commit/ff67d82e606c5829b1ddabb15c7a5886678af767))
* **hooks:** skip the session-end sync on /clear ([134bf31](https://github.com/arminzou/dotbrain/commit/134bf3159a52ea493468a733d55b831f6798c5d7))
* **site:** start the preview server without a reverse-DNS lookup ([7b9357b](https://github.com/arminzou/dotbrain/commit/7b9357b114b7239302e89192ce0a0962ad44e6ac))
* **sync:** compare conflict copy names with HEAD case-insensitively ([220733f](https://github.com/arminzou/dotbrain/commit/220733f00991bc48049d5eddaa0e914de364d8c5))
* **sync:** keep tracked files and clean up when a merge abort fails ([545bc64](https://github.com/arminzou/dotbrain/commit/545bc640c962985a88f14e06fed6898637a9b996))
* **sync:** remove conflict copies left by a failed merge ([86fc2a5](https://github.com/arminzou/dotbrain/commit/86fc2a51729e07a0c3d2a01fe8e8b7c9c5c896f9))


### Performance Improvements

* **sync:** read the home's state with one git status ([bd4c0f2](https://github.com/arminzou/dotbrain/commit/bd4c0f2a30b29a38178f74def00c0e42ac4bd3ef))


### Documentation

* **convention:** say when agents commit Brain changes by hand ([cfed120](https://github.com/arminzou/dotbrain/commit/cfed1207ca5fc9a0ecfba2603a39e6ed719667ef))
* **rules:** keep tests parallel-safe and Git work off hot paths ([a9f3529](https://github.com/arminzou/dotbrain/commit/a9f3529fc00fd187f8440e63289844a2f4caa015))
* **skills:** stack a branch only on work it depends on ([f24169b](https://github.com/arminzou/dotbrain/commit/f24169b7dd73366439023343b174cd869e2cd9ac))

## [0.11.0](https://github.com/arminzou/dotbrain/compare/v0.10.0...v0.11.0) (2026-10-20)


### ⚠ BREAKING CHANGES

* **sync:** home sync is on by default. The first session after upgrading commits everything uncommitted in ~/dotbrain and pushes it with any unpushed commits. Before upgrading, commit what you want to keep, discard or .gitignore anything that must not be pushed, or set `sync: enabled: false` in ~/dotbrain/config.yaml. Codex users must trust the new hooks once through /hooks.

### Features

* **sync:** sync the dotbrain home automatically ([#29](https://github.com/arminzou/dotbrain/issues/29)) ([1748b75](https://github.com/arminzou/dotbrain/commit/1748b751b72f17fe042a836ae0698dacbdde2711))

## [0.10.0](https://github.com/arminzou/dotbrain/compare/v0.9.0...v0.10.0) (2026-10-17)


### Features

* **skills:** suggest mechanical enforcement for promoted retro rules ([cd66642](https://github.com/arminzou/dotbrain/commit/cd666421f26b62ff56e04c3909edebc273d90d4b))


### Bug Fixes

* **skills:** tighten retro enforcement wording after review ([4f1e3ae](https://github.com/arminzou/dotbrain/commit/4f1e3ae1e4e5b8d0a2dfaf6a1be3d4f144830708))

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
