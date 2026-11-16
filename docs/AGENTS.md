# docs/AGENTS.md

This directory is the public docs site: VitePress, deployed to GitHub Pages by
`.github/workflows/docs.yml` on every push to `main` that touches `docs/`.

Before creating or revising guidance agents consume, read the shared
[writing reference](../plugin/skills/maintain-brain/references/writing.md).

```bash
cd docs && npm ci && npm run dev     # preview with live reload
npm run build                        # must pass before a push
```

## Pages

- `cli-reference.md` is generated from the CLI's command definitions. Never edit it by hand; change
  the help text in `src/dotbrain/cli.py` or the groups in `src/dotbrain/_cli_reference.py`, then
  regenerate with `uv run python -m dotbrain._cli_reference`.
- `configuration.md` is tested: `tests/test_configuration_docs.py` loads the first YAML block under
  ``## `config.yaml` `` and ``## `project.yaml` `` through the real config loader. Keep those
  headings exact, keep the fences plain ```` ```yaml ````, and keep every key the test reads.
- `zh/` holds the Simplified Chinese pages, one per English page with the same file name. They are
  hand-maintained, best effort: preserve the English facts and structure, using short, natural
  Chinese sentences rather than literal translations or stacked passives. Keep commands, code,
  diagrams and terms developers know in English (Agent, Coding Agent, PR, gitignore, worktree,
  checkout, thread) as is. When translating a
  heading that is a link target, keep the English slug with `{#english-slug}`. `zh/cli-reference.md`
  is a hand translation, not generated. Chinese nav and sidebar live under `locales.zh` in
  `.vitepress/config.mts`.
- Name a code block's file in a `# path` comment on its first line. A `[title]` after the language
  only renders inside a `::: code-group`.
- Use `::: code-group` for alternatives (Claude Code / Codex, macOS / Windows, uv / pipx).
- Check every claim against the code before writing it. Say what dotbrain does, not what a
  neighbouring tool does (Beads, the agent runtime).
- Add a new page to the sidebar in `.vitepress/config.mts` and to the index in `README.md`.
- VitePress compiles Markdown into Vue templates. Keep literal commands and placeholders in code;
  use `v-pre` for literal template expressions. Put page logic in `<script setup>`, keep it
  SSR-compatible, and access browser APIs only after mounting.
- Prefer VitePress's native containers, details, code groups, and highlighting before adding HTML
  or theme classes. Check `package.json`, the lockfile, and theme integration before assuming
  support for an extension. Use the [VitePress guide](https://vitepress.dev/guide/markdown) for syntax.

## Diagrams

These conventions apply to this public documentation site:

- Diagrams are drawn by `.vitepress/theme/Mermaid.vue`. Font, size, and colours live there and in
  `.vitepress/theme/style.css`; never style a single diagram.
- The content column is 688px. Preview the page and confirm each diagram draws, fits without
  scrolling, and has no clipped label in both light and dark themes. A passing build does not
  prove browser rendering.
- A list of steps with no branches is the HTML step strip, `<ol class="flow-steps">`.
- Give every Mermaid diagram an `accTitle` and describe its key steps in the surrounding prose.
  Use flowcharts for branches and shared flow, sequence diagrams for exchanges, state diagrams
  for lifecycles, and supported tree views for directory layouts.
- Use short IDs and quoted labels. Two-line labels have a bold name followed by a plain
  description; one-line labels stay plain. Italicize paths in supported diagram types and use
  plain verb phrases for arrow labels. Sequence labels stay plain and short, without `<br/>`.
- Let theme defaults own styling. Avoid reserved IDs such as `end`, backticks nested inside
  Markdown-string labels, and per-diagram colours. Check the installed renderer and the
  [Mermaid syntax reference](https://mermaid.js.org/intro/syntax-reference.html) when needed.
