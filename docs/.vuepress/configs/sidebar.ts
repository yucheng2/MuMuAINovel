export const sidebarConfig = {
  '/guide/': [
    {
      text: '指南',
      children: [
        '/guide/README.md',
        '/guide/intro.md',
        '/guide/quick-start.md',
        '/guide/installation.md',
        '/guide/usage.md',
        '/guide/deployment.md',
      ],
    },
  ],
  '/backend/': [
    {
      text: '后端文档',
      children: [
        '/backend/README.md',
        '/backend/architecture.md',
        '/backend/api.md',
        '/backend/ai-service.md',
        '/backend/mcp.md',
        '/backend/database.md',
      ],
    },
  ],
  '/frontend/': [
    {
      text: '前端文档',
      children: [
        '/frontend/README.md',
        '/frontend/components.md',
        '/frontend/pages.md',
        '/frontend/state.md',
      ],
    },
  ],
  '/config/': [
    {
      text: '配置文档',
      children: [
        '/config/README.md',
        '/config/environment.md',
        '/config/ai-providers.md',
      ],
    },
  ],
}
