# VitePress pages

Read this when writing a VitePress page or when a page builds but renders wrongly.
It says how VitePress treats a page and which
native feature to reach for; the official guide holds the syntax details.

## How a page is built

"Each Markdown file is compiled into HTML and then processed as a Vue Single-File Component"
([Using Vue in Markdown](https://vitepress.dev/guide/using-vue)). These consequences follow:

- Raw HTML passes through Markdown unchanged and becomes part of a Vue template, so it works, but it
  also gets Vue's rules: `{{ }}` is evaluated and a bare `<` opens a tag. Root-level
  `<script setup>` and `<style>` blocks, placed after the frontmatter, work as in a Vue component.
- A plain `<script>` inside the page body stays in the pre-rendered HTML but is dropped from the
  page's client code. It runs when the page is opened directly and silently does nothing when the
  reader arrives by a sidebar or next-page link, and the build does not warn. Put page logic in
  `<script setup>`.
- Vue directives work in the HTML: `v-model`, `@click`, `v-if`. They allow interactive content
  without a custom component.
- Pages are rendered at build time, so page logic must be SSR-compatible: no browser-only APIs
  such as `window` outside Vue's mount hooks.

## Prefer a native feature

Before writing HTML or adding a class to the theme, look for the need here. Every row is part of
VitePress's [Markdown extensions](https://vitepress.dev/guide/markdown) unless noted.

| Need | Native feature |
|---|---|
| Note, tip, warning, danger box | Custom containers: `::: tip Title` … `:::` |
| Collapsible answer | `::: details Question?` … `:::` |
| GitHub-style callout | Alerts: `> [!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]`, `[!CAUTION]` |
| Point at specific code lines | Line highlighting: a fence opened with `csharp{4,7-9}`, or `// [!code highlight]` |
| Show a before/after change | Colored diffs: `// [!code --]` and `// [!code ++]` on lines |
| Draw attention to one line | Focus: `// [!code focus]` |
| The same step in Bash and PowerShell | Code groups: `::: code-group` around labelled fences |
| Literal `{{ }}` in text | `v-pre` on an element, or a `::: v-pre` container ([Using Vue](https://vitepress.dev/guide/using-vue)) |
| A small status label | The default theme's `<Badge type="tip" text="…" />` component ([Badge](https://vitepress.dev/reference/default-theme-badge)) |
| Checklists, footnotes | Task lists and footnotes |
| An on-page contents list | `[[toc]]`; the right-hand outline already lists `##` and `###` headings |

Check the project's configuration before using extensions:

- **Importing code snippets** (`<<< @/path`) and **Markdown file inclusion** need source paths
  accessible to the documentation build. Use a permalink for code outside that source tree.
- **Math equations** need math rendering configured; otherwise use a code block or plain text.
- **Mermaid diagrams** need a rendering integration. Check the theme or plugins before adding
  `mermaid` fences. [mermaid.md](./mermaid.md) has diagram guidance.

## When the native set runs out

Write the smallest HTML that does the job and reuse the project's theme styles.
A behaviour several pages need can use a shared Vue component registered in the project's
VitePress theme.

The guide at vitepress.dev may describe a different release from the project's installed
VitePress version. Check the project's manifest and lockfile before working around a feature
that does not render.
