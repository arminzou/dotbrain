# Changelog

## [0.15.2](https://github.com/arminzou/dotbrain/compare/v0.15.1...v0.15.2) (2026-10-31)


### Documentation

* polish public guides and clarify runtime support ([a29b3f3](https://github.com/arminzou/dotbrain/commit/a29b3f362df99505335651c35ee9dfa092e6d0ff))

## [0.15.1](https://github.com/arminzou/dotbrain/compare/v0.15.0...v0.15.1) (2026-10-29)


### Bug Fixes

* **cli:** keep the tracked-link warning for files under a link and number doctor progress uniquely ([236e157](https://github.com/arminzou/dotbrain/commit/236e157471ef62cdabcaf9722444f3db89de2391))
* **skills:** use bounded completion waits for Codex workers ([#79](https://github.com/arminzou/dotbrain/issues/79)) ([b8c5f32](https://github.com/arminzou/dotbrain/commit/b8c5f32f3e4228bd1fc4fa1743432f345f17958c))


### Performance Improvements

* **cli:** look up machine facts once per run in refresh, doctor and bootstrap ([ef47138](https://github.com/arminzou/dotbrain/commit/ef47138a833ef6ff46cc9040f5a8d0b937be6df6))


### Documentation

* **site:** cut the homepage wiring to three steps and close with a call to action ([cd0c5ba](https://github.com/arminzou/dotbrain/commit/cd0c5ba46cc17b61bdfc571af1c31f86b6bda807))
* **site:** redesign the homepage around the second-brain message ([de4851e](https://github.com/arminzou/dotbrain/commit/de4851e16faef2df92a1f16b3fcd6f224554add2))
* **site:** replace the social preview with 1200x630 cards ([3a2ba7b](https://github.com/arminzou/dotbrain/commit/3a2ba7be1bd87857b54d73734e624d125e229886))
* **site:** show the Brainspace and repo contents as a static panel ([b19c25a](https://github.com/arminzou/dotbrain/commit/b19c25a2b131d1c979821fb74c7bd7bf8020a7c3))

## [0.15.0](https://github.com/arminzou/dotbrain/compare/v0.14.0...v0.15.0) (2026-10-27)


### ⚠ BREAKING CHANGES

* Packaged Claude subagents now require a wired checkout. Run dotbrain refresh to deliver the roles selected in project.yaml under dotbrain-<role> names. Global linking manages custom subagents only.

### Features

* **evals:** run core skill evals on Claude Code and Codex with Promptfoo ([#60](https://github.com/arminzou/dotbrain/issues/60)) ([9b51ad2](https://github.com/arminzou/dotbrain/commit/9b51ad212537d74c4c005ebed8f51602878363d7))
* make packaged subagents optional per project ([#69](https://github.com/arminzou/dotbrain/issues/69)) ([da610b1](https://github.com/arminzou/dotbrain/commit/da610b16071e08c8c0d89266ef99af163f005b9b))
* **skills:** curate retrospectives from work records and use findings before work ([#65](https://github.com/arminzou/dotbrain/issues/65)) ([7965b7a](https://github.com/arminzou/dotbrain/commit/7965b7ae4bccc770998655e9b5fc74aabd692873))
* **skills:** let workflow skills start from plain requests ([#63](https://github.com/arminzou/dotbrain/issues/63)) ([4291008](https://github.com/arminzou/dotbrain/commit/42910085da22217c4eb74f7e3af6ae52e02431a6))
* **skills:** record acceptance evidence kinds and exemptions ([62ac0bd](https://github.com/arminzou/dotbrain/commit/62ac0bda4c8861eb012666b083f4a6e887665b0f))
* **wiring:** give agents an ignored .dotbrain-tmp folder for comment files ([#73](https://github.com/arminzou/dotbrain/issues/73)) ([e5114af](https://github.com/arminzou/dotbrain/commit/e5114af29c876d598afdd0ac8af7179aadf06327))


### Bug Fixes

* **bootstrap:** migrate legacy global profile configuration ([#66](https://github.com/arminzou/dotbrain/issues/66)) ([95c330c](https://github.com/arminzou/dotbrain/commit/95c330c1b926a01868c9dc24ce0776c7833b01bc))
* **codex:** migrate project skills to .agents/skills ([#62](https://github.com/arminzou/dotbrain/issues/62)) ([e3e2fc0](https://github.com/arminzou/dotbrain/commit/e3e2fc0f9f439deea9f1428aa1802469e5f1db6e))
* probe .cmd runtime CLIs on Windows and add an opt-in delivery UAT suite ([#59](https://github.com/arminzou/dotbrain/issues/59)) ([949f71c](https://github.com/arminzou/dotbrain/commit/949f71c36944e3458895706aaa70b695702fb191))
* **refresh:** warn when global settings still need migration ([e98d044](https://github.com/arminzou/dotbrain/commit/e98d0442a2dc1f5d62c0bec4079e124a41827f44))
* **skills:** keep static-only evidence exclusive ([295903d](https://github.com/arminzou/dotbrain/commit/295903d62ad118f2299241b23a4578567a0bcdc9))
* **skills:** route worker dispatch through run-execution on both runtimes ([#64](https://github.com/arminzou/dotbrain/issues/64)) ([62c8567](https://github.com/arminzou/dotbrain/commit/62c856710bded06c7bf6327dcf5d10b2eb0a7bcf))
* stabilize sync tests and recover retro candidates ([#67](https://github.com/arminzou/dotbrain/issues/67)) ([6f152da](https://github.com/arminzou/dotbrain/commit/6f152da11ebe4dc32634ca38363fa7a61d46807a))
* **tests:** bound heavy checks and pytest worker concurrency ([#70](https://github.com/arminzou/dotbrain/issues/70)) ([9a9ef4c](https://github.com/arminzou/dotbrain/commit/9a9ef4c881f69723d672726c38dcfacc97f96154))

## [0.14.0](https://github.com/arminzou/dotbrain/compare/v0.13.0...v0.14.0) (2026-10-23)


### ⚠ BREAKING CHANGES

* teach-me and triage-public are explicit-only; invoke them by name.

### Features

* slim execution skills, store agent records, warn on drift ([#57](https://github.com/arminzou/dotbrain/issues/57)) ([5f4f4c3](https://github.com/arminzou/dotbrain/commit/5f4f4c3ae320291dfc3e5b5809672acc7254c817))

## [0.13.0](https://github.com/arminzou/dotbrain/compare/v0.12.0...v0.13.0) (2026-10-23)


### ⚠ BREAKING CHANGES

* **runtimes:** Projects without agents now follow machine setup. Set agents: [claude, codex] to retain the previous runtime selection. Refresh also preserves undeclared workspaces instead of pruning them.

### Features

* **agents:** deliver global subagents to runtime profiles ([#53](https://github.com/arminzou/dotbrain/issues/53)) ([60b05e1](https://github.com/arminzou/dotbrain/commit/60b05e1b1e8076f6143695680c99cb3e93d4bc6e))
* **bootstrap:** set up every working runtime on a machine's first run ([#55](https://github.com/arminzou/dotbrain/issues/55)) ([a61215b](https://github.com/arminzou/dotbrain/commit/a61215b9ae307efc02ad1e4e0fcec4a1eb869ef0))
* **cli:** detach dotbrain's machine-wide delivery from a runtime ([#54](https://github.com/arminzou/dotbrain/issues/54)) ([bd5df2d](https://github.com/arminzou/dotbrain/commit/bd5df2d5bf63a1a0d4f44a277315296cc71a45a9))
* **cursor:** deliver skills and hooks to Cursor CLI ([#46](https://github.com/arminzou/dotbrain/issues/46)) ([da024f4](https://github.com/arminzou/dotbrain/commit/da024f4ea4585a12cd4965f784e684b2de5204a0))
* deliver skills and hooks to Hermes through a shared runtime description ([#41](https://github.com/arminzou/dotbrain/issues/41)) ([d94c532](https://github.com/arminzou/dotbrain/commit/d94c53264564109a83bb4d375d24f1ef96d89a2d))
* deliver skills and hooks to OpenCode ([#42](https://github.com/arminzou/dotbrain/issues/42)) ([0cda5d4](https://github.com/arminzou/dotbrain/commit/0cda5d4438b5d6132761f8ee2987b6a01447035a))
* **pi:** deliver dotbrain skills and hooks to Pi ([#44](https://github.com/arminzou/dotbrain/issues/44)) ([900749c](https://github.com/arminzou/dotbrain/commit/900749cfbe76c4030f09448ccfdc4b8372240934))
* **runtimes:** follow machine setup for undeclared projects ([#50](https://github.com/arminzou/dotbrain/issues/50)) ([a8e91cd](https://github.com/arminzou/dotbrain/commit/a8e91cd2cc35e08db0795cb5cc0ed4f781c9e010))
* **skills:** link global skills into runtime profiles ([#52](https://github.com/arminzou/dotbrain/issues/52)) ([adcb5a4](https://github.com/arminzou/dotbrain/commit/adcb5a406704b87a677f1a57eab017cb102c256a))


### Bug Fixes

* **refresh:** skip checkouts on another machine in --all ([3de1f09](https://github.com/arminzou/dotbrain/commit/3de1f09645178cd8fc2da80ece04a747ec29c7eb))


### Documentation

* stop tying Hermes, OpenCode, and Pi to one operating system ([479a8e9](https://github.com/arminzou/dotbrain/commit/479a8e98ca56a34288c3c365772e2eab2d45db86))

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
