import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import Mermaid from './Mermaid.vue'
import LearnOverview from './LearnOverview.vue'
import './custom.css'

// The dotbrain default theme. A Brain theme that replaces the default can extend this one to keep
// Mermaid diagrams and the Learn overview.
export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('Mermaid', Mermaid)
    app.component('LearnOverview', LearnOverview)
  }
} satisfies Theme
