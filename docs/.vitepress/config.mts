import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Dotbrain',
  description: 'Private project context for coding agents, kept out of your code repo.',
  base: '/dotbrain/',
  cleanUrls: true,
  lastUpdated: true,
  // README.md is the index for browsing docs/ on GitHub, and AGENTS.md/CLAUDE.md guide agents
  // editing docs/; index.md is the site's home.
  srcExclude: ['README.md', 'AGENTS.md', 'CLAUDE.md'],
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
  // English stays at the root so existing URLs keep working; zh/ mirrors its file names.
  locales: {
    root: { label: 'English', lang: 'en-US' },
    zh: {
      label: '简体中文',
      lang: 'zh-CN',
      link: '/zh/',
      description: '为 Coding Agent 提供私有的项目上下文，不放进公开代码仓库。',
      themeConfig: {
        nav: [
          { text: '指南', link: '/zh/getting-started', activeMatch: '^/zh/(why-dotbrain|getting-started|architecture|workflow|learning|wiring|session-context|beads-backend|brain-site|troubleshooting)' },
          { text: '参考', link: '/zh/cli-reference', activeMatch: '^/zh/(cli-reference|configuration|skills|glossary)' },
          { text: 'PyPI', link: 'https://pypi.org/project/dotbrain/' },
        ],
        sidebar: [
          {
            text: '指南',
            items: [
              { text: '为什么用 Dotbrain？', link: '/zh/why-dotbrain' },
              { text: '快速开始', link: '/zh/getting-started' },
            ],
          },
          {
            text: '使用场景',
            items: [
              { text: '开发项目', link: '/zh/workflow' },
              { text: '学习项目', link: '/zh/learning' },
              { text: '浏览 Brain', link: '/zh/brain-site' },
            ],
          },
          {
            text: '工作原理',
            items: [
              { text: '架构', link: '/zh/architecture' },
              { text: '项目连接', link: '/zh/wiring' },
              { text: '会话上下文', link: '/zh/session-context' },
              { text: 'Beads 后端', link: '/zh/beads-backend' },
            ],
          },
          {
            text: '帮助',
            items: [{ text: '故障排查与常见问题', link: '/zh/troubleshooting' }],
          },
          {
            text: '参考',
            items: [
              { text: 'CLI 参考', link: '/zh/cli-reference' },
              { text: '配置', link: '/zh/configuration' },
              { text: 'Brain 站点配置', link: '/zh/brain-site-configuration' },
              { text: '技能', link: '/zh/skills' },
              { text: '术语表', link: '/zh/glossary' },
            ],
          },
        ],
        outline: { level: [2, 3], label: '本页目录' },
        editLink: {
          pattern: 'https://github.com/arminzou/dotbrain/edit/main/docs/:path',
          text: '在 GitHub 上编辑此页',
        },
        docFooter: { prev: '上一页', next: '下一页' },
        lastUpdated: { text: '最后更新' },
        langMenuLabel: '切换语言',
        returnToTopLabel: '回到顶部',
        sidebarMenuLabel: '菜单',
        darkModeSwitchLabel: '外观',
        lightModeSwitchTitle: '切换到浅色模式',
        darkModeSwitchTitle: '切换到深色模式',
        footer: { message: '基于 MIT 许可证发布。' },
      },
    },
  },
  transformHead: ({ title, description }) => [
    ['meta', { property: 'og:title', content: title }],
    ['meta', { property: 'og:description', content: description }],
  ],

  markdown: {
    theme: { light: 'github-light', dark: 'github-dark' },
    // A ```mermaid fence becomes the theme's <Mermaid> component, which draws it in the browser.
    config(md) {
      const fence = md.renderer.rules.fence!
      md.renderer.rules.fence = (tokens, index, ...rest) =>
        tokens[index].info.trim() === 'mermaid'
          ? `<Mermaid code="${encodeURIComponent(tokens[index].content)}" />`
          : fence(tokens, index, ...rest)
    },
  },

  themeConfig: {
    logo: {
      light: { src: '/assets/mark-light.png', width: 24, height: 24 },
      dark: { src: '/assets/mark-dark.png', width: 24, height: 24 },
      alt: 'Dotbrain',
    },
    nav: [
      { text: 'Guide', link: '/getting-started', activeMatch: '^/(why-dotbrain|getting-started|architecture|workflow|learning|wiring|session-context|beads-backend|brain-site|troubleshooting)' },
      { text: 'Reference', link: '/cli-reference', activeMatch: '^/(cli-reference|configuration|skills|glossary)' },
      { text: 'PyPI', link: 'https://pypi.org/project/dotbrain/' },
    ],
    sidebar: [
      {
        text: 'Guide',
        items: [
          { text: 'Why Dotbrain?', link: '/why-dotbrain' },
          { text: 'Getting started', link: '/getting-started' },
        ],
      },
      {
        text: 'Use cases',
        items: [
          { text: 'Develop a project', link: '/workflow' },
          { text: 'Learn your project', link: '/learning' },
          { text: 'Browse the Brain', link: '/brain-site' },
        ],
      },
      {
        text: 'How it works',
        items: [
          { text: 'Architecture', link: '/architecture' },
          { text: 'Wiring', link: '/wiring' },
          { text: 'Session context', link: '/session-context' },
          { text: 'Beads backend', link: '/beads-backend' },
        ],
      },
      {
        text: 'Help',
        items: [{ text: 'Troubleshooting & FAQ', link: '/troubleshooting' }],
      },
      {
        text: 'Reference',
        items: [
          { text: 'CLI reference', link: '/cli-reference' },
          { text: 'Configuration', link: '/configuration' },
          { text: 'Brain site configuration', link: '/brain-site-configuration' },
          { text: 'Skills', link: '/skills' },
          { text: 'Glossary', link: '/glossary' },
        ],
      },
    ],
    outline: { level: [2, 3], label: 'On this page' },
    search: { provider: 'local' },
    socialLinks: [{ icon: 'github', link: 'https://github.com/arminzou/dotbrain' }],
    editLink: {
      pattern: 'https://github.com/arminzou/dotbrain/edit/main/docs/:path',
      text: 'Edit this page on GitHub',
    },
    footer: { message: 'Released under the MIT License.' },
  },
})
