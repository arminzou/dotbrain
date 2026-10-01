# docs/AGENTS.md

This directory is the public docs site: VitePress, deployed to GitHub Pages by
`.github/workflows/docs.yml` on every push to `main` that touches `docs/`.

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
- Name a code block's file in a `# path` comment on its first line. A `[title]` after the language
  only renders inside a `::: code-group`.
- Use `::: code-group` for alternatives (Claude Code / Codex, macOS / Windows, uv / pipx).
- Check every claim against the code before writing it. Say what dotbrain does, not what a
  neighbouring tool does (Beads, the agent runtime).
- Add a new page to the sidebar in `.vitepress/config.mts` and to the index in `README.md`.

## Diagrams

Follow the dotbrain Mermaid guide,
[`plugin/skills/brain-site/references/mermaid.md`](../plugin/skills/brain-site/references/mermaid.md):
diagram type, label style (bold name over a plain line, italic paths, verb arrow labels), fit, and
pitfalls. It is the convention for every project dotbrain wires; this site follows it too.

What is specific to this site:

- Diagrams are drawn by `.vitepress/theme/Mermaid.vue`. Font, size, and colours live there and in
  `.vitepress/theme/style.css`; never style a single diagram.
- The content column is 688px. Preview the page and confirm each diagram draws, fits without
  scrolling, and has no clipped label.
- A list of steps with no branches is the HTML step strip, `<ol class="flow-steps">`.
