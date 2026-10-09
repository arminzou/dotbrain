---
name: brain-site
description: Set up, maintain, build, and preview a Brain's private site with dotbrain site, including navigation, themes, and rendering checks.
disable-model-invocation: true
---

# Brain Site

A **Brain site** is the private site dotbrain renders from one Brain. Every Markdown file in the
Brain is a page, served at its path in the Brain, so relative links between Brain files work on the
site. The Brain owns its content, `.brain/site/site.yaml` (whose nav is the sidebar), the home page
`.brain/site/index.md`, and optional theme extensions; dotbrain owns the engine, which
`dotbrain site` runs from its cache. This skill picks the command, keeps the sidebar, and supplies
the page syntax. It never publishes anything: a Brain site is served on `127.0.0.1` only, and a
project's public docs are not a Brain site.

This skill expects `dotbrain site` from dotbrain 0.4.6 or later, which needs Node 22.12 or later.

## Choose the branch

- **Requested site setup, and the Brain has no `.brain/site/`:** set one up (below).
- **Requested work on an existing site:** find the request in the command table.
- **Writing a page that needs more than plain Markdown:** read
  [publishing.md](references/publishing.md) for lessons and references,
  [vitepress.md](references/vitepress.md) for page pitfalls and native features, and
  [mermaid.md](references/mermaid.md) before drawing a diagram, on the site or in any other
  project doc.

## Setting up a site

1. Run `dotbrain site init` from the wired repo, or `dotbrain site init --project <project>`. It
   creates `.brain/site/site.yaml`, whose nav lists every `docs/` page (root pages under Docs, one
   section per folder), the standard home page `.brain/site/index.md`, and the manual
   `.brain/site/configure.md`, which explains the settings. It never overwrites a file.
2. Review the generated sidebar with the user: propose trimming it to the pages read often, and
   grouping and naming sections the way a reader would look for them. Trimming never takes a page
   off the site. Confirm before editing.
3. If the Brain has a `learning/` workspace, tell `teach-me` about the site: add a Learning site
   section to `learning/AGENTS.md` that points at this skill's publishing guide.
4. Run `dotbrain site build`. It fails on every link to a missing file in the Brain; fix those
   with the user (usually a renamed ADR or a deleted doc), then offer `dotbrain site dev`.

## Command table

Commands default to the current wired project, including a worktree or nested directory. Use
`--project <name>` from elsewhere and `--home <path>` for a different private data root. Finite
`site init` and `site build` reports support `--json`; `site dev` and `site preview` stream the
server output and do not accept JSON reporting.

| Request or symptom | Do |
|---|---|
| Look at the site while editing | `dotbrain site dev`; restart it after changing `site.yaml` |
| Check that the site builds | `dotbrain site build` |
| Serve the last build | `dotbrain site preview` |
| Add a `docs/` page to the sidebar | Add it to a nav section in `site.yaml` by its path relative to `docs/` (`#section` may follow) |
| Take a page out of the sidebar | Remove its nav entry; the page stays on the site, reached by links and search |
| Take a page off the site | Only by deleting, moving out of the Brain, or renaming the file with `[brackets]`: every Markdown file in the Brain is a page |
| `nav links to pages that do not exist` | The listed page was moved or deleted: fix the link or remove the entry |
| ``` `topic` must be one of the MISSION.md topics ``` | Match the page's `topic` to a `### ` heading under `## Topics`, or add the topic with the user; `(none)` means `learning/MISSION.md` is missing or has no topics |
| `index.md at the Brain's root takes the home page's address` | Rename or move `.brain/index.md`; the home page is `.brain/site/index.md` |
| `Found dead link` | A page links a file that does not exist; the message names the page and line. Fix the link to the renamed file, or remove it |
| `needs Node 22.12 or later` | Tell the user; nothing else in dotbrain needs Node |
| `installing the site engine failed` | Read npm's lines in the message: the first run of a dotbrain version needs network access for `npm ci` |
| `vitepress build failed for <name>` | Read VitePress's error above it: usually a dead link, invalid frontmatter, or a page that does not compile ([vitepress.md](references/vitepress.md)) |
| `has no build to preview` | Run `dotbrain site build` first |
| `cannot serve on 127.0.0.1:4173` | Another preview holds the port: stop it first |
| `no .brain found here` | Run from a wired repo or pass `--project <project>` |
| A page builds but renders wrongly | [vitepress.md](references/vitepress.md), then [mermaid.md](references/mermaid.md) for diagrams |
| Change the look | `.brain/site/theme/style.css`, loaded after the defaults |
| Add a component | `.brain/site/theme/index.ts` exporting `{ enhanceApp({ app }) { ... } }` |
| Replace the theme | `.brain/site/theme/index.ts` exporting a whole theme; extend `@dotbrain/theme` to keep Mermaid, `<DocsOverview />`, `<LearnOverview />`, and the status badge. The default styles still load; override them in `style.css` |

Every Markdown file in the Brain is published, except symlinks and names with brackets; the nav
only decides the sidebar. ADRs show their `status` and design docs their `lifecycle` as a badge.
`.brain/site/index.md` is the home page and the user's to change. The standard one shows the site's
title and description with three buttons (Docs; Start learning when there is a lesson; Configure
this site), then `<DocsOverview />` (one tile per `docs/` folder) and `<LearnOverview />` (one tile per
Learn topic, latest lessons first), each with its most active six tiles and the rest on one line; it
shows only `docs/` and `learning/`. A `hero` in its frontmatter replaces the standard hero.
`.brain/site/configure.md` is dotbrain's manual for the settings: `dotbrain refresh` overwrites
it, so never edit it. Theme extensions can import only what the engine
installs (Vue, VitePress, Mermaid) and their own local files; a Brain cannot add npm packages. A
theme change is a site change: agree it with the user first.

Because every Brain file is a page, any Brain edit can break the build: a renamed file leaves dead
links, and invalid frontmatter or Vue syntax in prose stops compilation. After renaming or deleting
a Brain file, search the Brain for links to it.

## Verification

Before calling a site change done:

- `dotbrain site build` passes.
- The sidebar lists what the user reads often, grouped the way they look for it.
- New or changed diagrams and custom HTML were looked at in `dotbrain site dev`: a Mermaid parse
  error shows only on the page, not in the build.
- Nothing from the Brain or the site's build output was copied into the code repo.
