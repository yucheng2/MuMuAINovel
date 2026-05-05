import { defineUserConfig } from 'vuepress'
import { defaultTheme } from '@vuepress/theme-default'
import { navbarConfig } from './configs/navbar'
import { sidebarConfig } from './configs/sidebar'

export default defineUserConfig({
  lang: 'zh-CN',
  title: 'MuMuAINovel',
  description: 'AI 智能小说创作助手',

  base: '/',

  head: [
    ['link', { rel: 'icon', href: '/images/logo.png' }],
    ['meta', { name: 'theme-color', content: '#3eaf7c' }],
  ],

  theme: defaultTheme({
    logo: '/images/logo.png',
    repo: 'yucheng2/MuMuAINovel',
    docsDir: 'docs',
    editLink: true,
    editLinkText: '编辑此页',
    lastUpdated: true,
    lastUpdatedText: '上次更新',
    contributors: false,
    navbar: navbarConfig,
    sidebar: sidebarConfig,
    colorModeSwitch: true,
  }),

  plugins: [],
})
