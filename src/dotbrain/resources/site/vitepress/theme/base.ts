import { h } from 'vue'
import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import Mermaid from './Mermaid.vue'
import DocsOverview from './DocsOverview.vue'
import LearnOverview from './LearnOverview.vue'
import PageStatus from './PageStatus.vue'
import './custom.css'

// The dotbrain default theme. A Brain theme that replaces the default can extend this one to keep
// Mermaid diagrams, the home page's docs and Learn overviews, and the status badge on ADRs and
// design docs.
export default {
  extends: DefaultTheme,
  Layout: () => h(DefaultTheme.Layout, null, { 'doc-before': () => h(PageStatus) }),
  enhanceApp({ app }) {
    app.component('Mermaid', Mermaid)
    app.component('DocsOverview', DocsOverview)
    app.component('LearnOverview', LearnOverview)
  }
} satisfies Theme
