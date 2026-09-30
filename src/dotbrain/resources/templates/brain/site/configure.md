# Configuring this site

`dotbrain site` renders this site from the Brain, for this machine only: it is served on
`127.0.0.1` and never published. dotbrain owns this page, `.brain/site/configure.md`, and
`dotbrain refresh` keeps it current, so edits to it are overwritten.

## What is on the site

Every Markdown file in the Brain is a page, served at its path in the Brain: `docs/release.md` at
`/docs/release`, `adr/0001-example.md` at `/adr/0001-example`. So any relative link that works in
the Brain works here, and search finds every page. ADRs show their `status` and design docs their
`lifecycle` above the page.

Two kinds of file are skipped: symlinks, and files with `[brackets]` in their name, which VitePress
reads as route templates.

## The home page

`.brain/site/index.md` is the home page, served at `/`. The standard one shows:

- The site's `title` and `description` from `site.yaml`, and three buttons: **Docs** opens the
  first sidebar page (or the first `docs/` page), **Start learning** opens the first lesson when
  `learning/` has one, and **Configure this site** opens this page.
- `<DocsOverview />`: one tile per `docs/` folder, with its page count and most recently updated
  pages.
- `<LearnOverview />`: one tile per Learn topic, with its latest lessons, when `learning/` has any.
  The sidebar's Learn section lists every lesson in order.
- Each section shows its most recently active tiles first, at most six; any more are listed on one
  line below them, so the home page stays the same size however much the Brain grows.

The home page shows only `docs/` and `learning/`. ADRs, design docs, and every other Brain file are
on the site too, reached through links and search.

The home page is yours to change. Rearrange or remove the two components, add your own content
below them, or set your own hero in its frontmatter, which replaces the standard one:

```yaml
---
layout: home
hero:
  name: My Brain
  tagline: What this Brain is for.
  actions:
    - { theme: brand, text: Architecture, link: /docs/architecture }
---
```

## The sidebar

`.brain/site/site.yaml`'s `nav` decides what the sidebar lists. It never adds or removes pages:
a page left out of the nav is still on the site, reached by links and search. Items link `docs/`
pages by their path relative to `docs/`.

`dotbrain site init` listed every page in `docs/` at the time. Trim it to what you read often,
group pages into sections, and rename items. A page added to `docs/` later appears in the sidebar
only once you add it.

```yaml
title: "My Brain"
description: Private project guidance
nav:
  - text: Runbooks
    items:
      - { text: Release, link: runbooks/release }
      - { text: Deploy steps, link: "runbooks/deploy#steps" }
      - { text: Azure overview, link: deployment/azure/ }
```

- An item names a page as `runbooks/release` or `runbooks/release.md`, and may end in `#section`.
- A folder link ending in `/` names that folder's `README.md` or `index.md`.
- A home page kept in `docs/index.md` from an older setup belongs in `.brain/site/index.md`.

## Learn

When the Brain has a `learning/` workspace, its lessons and references also get a Learn section at
the top of the sidebar, grouped by the topics in `learning/MISSION.md`. Nothing in `site.yaml`
controls Learn.

## Commands

| Command | Does |
|---|---|
| `dotbrain site dev` | Serves the site with live reload; restart it after changing `site.yaml` |
| `dotbrain site build` | Builds the site into dotbrain's cache, never into the Brain |
| `dotbrain site preview` | Serves the last build |

Run them from the project repo, or pass `--name <project>` from anywhere.

## What fails the build

- A nav item linking a page that does not exist.
- A link on any page to a file that does not exist, such as a renamed ADR. The error names the
  file and line.
- Invalid YAML frontmatter on any page.
- A lesson or reference whose `topic` is not a `learning/MISSION.md` topic.

Every Brain edit, including an agent's, has to keep the site building.

## Changing the look

- `.brain/site/theme/style.css` loads after the default styles; override anything there.
- `.brain/site/theme/index.ts` exporting `{ enhanceApp({ app }) { ... } }` registers your own Vue
  components for pages to use.
- `.brain/site/theme/index.ts` exporting a whole theme replaces the default; extend
  `@dotbrain/theme` to keep Mermaid diagrams, the home page's overviews, and the status badge.

Theme files can import Vue, VitePress, Mermaid, and local files; a Brain cannot add npm packages.
A fenced `mermaid` code block draws a diagram on any page.
