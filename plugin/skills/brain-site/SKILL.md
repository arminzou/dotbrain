---
name: brain-site
description: Sets up, maintains, and builds a Brain site, the private site dotbrain renders from a Brain's docs/ and learning/, by driving `dotbrain site`. Use when giving a Brain a site, choosing which docs it publishes, previewing or building it, fixing a failed site build, or writing site pages that need VitePress or Mermaid syntax.
---

# Brain Site

A **Brain site** is the private site dotbrain renders from one Brain. The Brain owns its content,
`.brain/site/site.yaml`, and optional theme extensions; dotbrain owns the engine, which
`dotbrain site` runs from its cache. This skill picks the command, keeps the nav, and supplies the
page syntax. It never publishes anything: a Brain site is served on `127.0.0.1` only, and a
project's public docs are not a Brain site.

This skill expects `dotbrain site` from dotbrain 0.4.6 or later, which needs Node 22.12 or later.

## Choose the branch

- **The Brain has no `.brain/site/`:** set one up (below).
- **The Brain has a site:** find the request in the command table.
- **Writing a page that needs more than plain Markdown:** read
  [publishing.md](references/publishing.md) for lessons and references,
  [vitepress.md](references/vitepress.md) for page pitfalls and native features, and
  [mermaid.md](references/mermaid.md) before drawing a diagram.

## Setting up a site

1. Run `dotbrain site init` from the wired repo, or `dotbrain site init --name <project>`. It
   creates `.brain/site/site.yaml` and a starter `docs/index.md`, and never overwrites a file.
2. List `docs/` and propose nav sections from it: the pages worth reading as a site, grouped the way
   a reader would look for them. Agent-oriented notes stay off. Confirm the nav with the user.
3. If the Brain has a `learning/` workspace, tell `teach-me` about the site: add a Learning site
   section to `learning/AGENTS.md` that points at this skill's publishing guide.
4. Run `dotbrain site build`, then offer `dotbrain site dev` to look at it.

## Command table

| Request or symptom | Do |
|---|---|
| Look at the site while editing | `dotbrain site dev` |
| Check that the site builds | `dotbrain site build` |
| Serve the last build | `dotbrain site preview` |
| Publish a `docs/` page | Add it to a nav section in `site.yaml` by its path relative to `docs/`, then build |
| Take a page off the site | Remove its nav entry; the page stays in `docs/` |
| `nav links to pages that do not exist` | The listed page was moved or deleted: fix the link or remove the entry |
| ``` `topic` must be one of the MISSION.md topics ``` | Match the page's `topic` to a `### ` heading under `## Topics`, or add the topic with the user |
| `needs Node 22.12 or later` | Tell the user; nothing else in dotbrain needs Node |
| `installing the site engine failed` | Read npm's lines in the message: the first run of a dotbrain version needs network access for `npm ci` |
| `vitepress build failed for <name>` | Read VitePress's error above it: usually a dead internal link or a page that does not compile ([vitepress.md](references/vitepress.md)) |
| `has no build to preview` | Run `dotbrain site build` first |
| `no .brain found here` | Run from a wired repo or pass `--name <project>` |
| A page builds but renders wrongly | [vitepress.md](references/vitepress.md), then [mermaid.md](references/mermaid.md) for diagrams |
| Change the look | `.brain/site/theme/style.css`, loaded after the defaults |
| Add a component | `.brain/site/theme/index.ts` exporting `{ enhanceApp({ app }) { ... } }` |
| Replace the theme | `.brain/site/theme/index.ts` exporting a whole theme; extend `@dotbrain/theme` to keep Mermaid and `<LearnOverview />`. The default styles still load; override them in `style.css` |

The nav is the allowlist: a `docs/` page not listed in `site.yaml` is not published, and that is not
an error. `docs/index.md` is always the home page; `<LearnOverview />` there lists the Learn topics.
Theme extensions can import only what the engine installs (Vue, VitePress, Mermaid) and their own
local files; a Brain cannot add npm packages. `dev` decides the published pages when it starts:
restart it after changing the nav or adding a page. A theme change is a site change: agree it with the
user first.

## Verification

Before calling a site change done:

- `dotbrain site build` passes.
- Every page the user expects is in the nav, and nothing agent-only was added to it.
- New or changed diagrams and custom HTML were looked at in `dotbrain site dev`: a Mermaid parse
  error shows only on the page, not in the build.
- Nothing from the Brain or the site's build output was copied into the code repo.
