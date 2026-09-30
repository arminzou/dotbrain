import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitepress'

// `dotbrain site` resolves everything Brain-specific (page addresses, sidebar, Learn) in Python and
// hands the result over as JSON; this file only turns it into VitePress config.
const settingsPath = process.env.DOTBRAIN_SITE_SETTINGS
if (!settingsPath) throw new Error('DOTBRAIN_SITE_SETTINGS is not set: run the site through `dotbrain site`')
const settings = JSON.parse(readFileSync(settingsPath, 'utf8'))

const themeDir = join(dirname(fileURLToPath(import.meta.url)), 'theme')
const engineRoot = dirname(dirname(fileURLToPath(import.meta.url)))
const norm = (path: string) => path.replace(/\\/g, '/').toLowerCase()
const brainRoot = norm(settings.brain).replace(/\/?$/, '/')
const brainTheme = join(settings.brain, 'site', 'theme')
const brainFile = (name: string, fallback: string) =>
  existsSync(join(brainTheme, name)) ? join(brainTheme, name) : join(themeDir, fallback)

export default defineConfig({
  title: settings.title,
  description: settings.description,
  head: [['link', { rel: 'icon', href: 'data:,' }]],
  // The Brain's real path: a repo reaches it through a link, and Vite resolves pages to real paths.
  srcDir: settings.brain,
  srcExclude: settings.exclude,
  outDir: settings.outDir,
  cacheDir: settings.cacheDir,
  rewrites: settings.rewrites,
  ignoreDeadLinks: 'localhostLinks',
  lastUpdated: true,
  // The home page gets the standard hero (title, tagline, and the Docs, Start learning, and
  // Configure this site buttons) unless its own frontmatter sets one.
  transformPageData(pageData) {
    if (pageData.filePath === 'site/index.md' && pageData.frontmatter.layout === 'home') {
      pageData.frontmatter.hero ??= settings.home.hero
    }
  },
  markdown: {
    // A ```mermaid fence becomes the theme's <Mermaid> component, which draws it in the browser.
    config(md) {
      const fence = md.renderer.rules.fence!
      md.renderer.rules.fence = (tokens, index, ...rest) =>
        tokens[index].info.trim() === 'mermaid'
          ? `<Mermaid code="${encodeURIComponent(tokens[index].content)}" />`
          : fence(tokens, index, ...rest)
    }
  },
  vite: {
    resolve: {
      alias: {
        '@dotbrain/theme': join(themeDir, 'base.ts'),
        '@brain/theme': brainFile('index.ts', 'empty.ts'),
        '@brain/style': brainFile('style.css', 'empty.css')
      }
    },
    plugins: [
      {
        // Brain pages and theme files live outside the engine, where no node_modules exists, so a
        // bare import from them (`vue`, `vitepress/theme`) resolves as if made from the engine.
        name: 'dotbrain:engine-dependencies',
        enforce: 'pre',
        async resolveId(source, importer, options) {
          if (!importer || !/^[@a-z]/i.test(source) || !norm(importer).startsWith(brainRoot)) return null
          return this.resolve(source, join(engineRoot, 'package.json'), { ...options, skipSelf: true })
        }
      }
    ]
  },
  themeConfig: {
    search: { provider: 'local' },
    nav: [{ text: 'Home', link: '/' }],
    sidebar: settings.sidebar,
    learn: settings.learn,
    docs: settings.home.docs
  }
})
