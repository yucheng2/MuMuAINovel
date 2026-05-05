import { navbar } from '@vuepress/theme-default'

export const navbarConfig = navbar([
  { text: '指南', link: '/guide/' },
  { text: '后端', link: '/backend/' },
  { text: '前端', link: '/frontend/' },
  { text: '配置', link: '/config/' },
  {
    text: '更多',
    children: [
      { text: '更新日志', link: '/CHANGELOG.md' },
      { text: 'GitHub', link: 'https://github.com/yucheng2/MuMuAINovel' },
    ],
  },
])
