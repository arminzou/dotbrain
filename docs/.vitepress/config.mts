import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Dotbrain',
  description: 'Private project context for coding agents, kept out of your code repo.',
  base: '/dotbrain/',
  cleanUrls: true,
  lastUpdated: true,
  // README.md is the index for browsing docs/ on GitHub; index.md is the site's home.
  srcExclude: ['README.md'],
  head: [
    ['link', { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/dotbrain/assets/favicon-light-32.png' }],
    ['link', { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/dotbrain/assets/favicon-light-32.png', media: '(prefers-color-scheme: light)' }],
    ['link', { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/dotbrain/assets/favicon-dark-32.png', media: '(prefers-color-scheme: dark)' }],
    ['link', { rel: 'apple-touch-icon', sizes: '180x180', href: '/dotbrain/assets/apple-touch-icon-light.png' }],
    ['meta', { property: 'og:site_name', content: 'Dotbrain' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:image', content: 'https://arminzou.github.io/dotbrain/assets/social-light.png' }],
    ['meta', { property: 'og:image:width', content: '1200' }],
    ['meta', { property: 'og:image:height', content: '630' }],
    ['meta', { property: 'og:image:alt', content: 'Dotbrain connected brain mark and wordmark' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['meta', { name: 'twitter:image', content: 'https://arminzou.github.io/dotbrain/assets/social-light.png' }],
    ['meta', { name: 'twitter:image:alt', content: 'Dotbrain connected brain mark and wordmark' }],
  ],
  transformHead: ({ title, description }) => [
    ['meta', { property: 'og:title', content: title }],
    ['meta', { property: 'og:description', content: description }],
  ],

  themeConfig: {
    logo: {
      light: { src: '/assets/mark-light.png', width: 24, height: 24 },
      dark: { src: '/assets/mark-dark.png', width: 24, height: 24 },
      alt: 'Dotbrain',
    },
    nav: [
      { text: 'Guide', link: '/getting-started', activeMatch: '^/(getting-started|architecture|wiring|beads-backend)' },
      { text: 'Reference', link: '/cli-reference', activeMatch: '^/(cli-reference|configuration|skills|glossary)' },
      { text: 'PyPI', link: 'https://pypi.org/project/dotbrain/' },
    ],
    sidebar: [
      {
        text: 'Guide',
        items: [
          { text: 'Getting started', link: '/getting-started' },
          { text: 'Architecture', link: '/architecture' },
          { text: 'Wiring', link: '/wiring' },
          { text: 'Beads backend', link: '/beads-backend' },
        ],
      },
      {
        text: 'Reference',
        items: [
          { text: 'CLI reference', link: '/cli-reference' },
          { text: 'Configuration', link: '/configuration' },
          { text: 'Skills', link: '/skills' },
          { text: 'Glossary', link: '/glossary' },
        ],
      },
    ],
    outline: [2, 3],
    search: { provider: 'local' },
    socialLinks: [{ icon: 'github', link: 'https://github.com/arminzou/dotbrain' }],
    editLink: {
      pattern: 'https://github.com/arminzou/dotbrain/edit/main/docs/:path',
      text: 'Edit this page on GitHub',
    },
    footer: { message: 'Released under the MIT License.' },
  },
})
