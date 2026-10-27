import { h } from 'vue'
import type { Theme } from 'vitepress'
import DefaultTheme from 'vitepress/theme'
import '@fontsource-variable/geist'
import '@fontsource-variable/geist-mono'
import HomeHero from './HomeHero.vue'
import Mermaid from './Mermaid.vue'
import SkillSpotlight from './SkillSpotlight.vue'
import WorkLoop from './WorkLoop.vue'
import './style.css'

export default {
  extends: DefaultTheme,
  Layout: () => h(DefaultTheme.Layout, null, { 'home-hero-before': () => h(HomeHero) }),
  enhanceApp({ app }) {
    app.component('Mermaid', Mermaid)
    app.component('SkillSpotlight', SkillSpotlight)
    app.component('WorkLoop', WorkLoop)
  },
} satisfies Theme
