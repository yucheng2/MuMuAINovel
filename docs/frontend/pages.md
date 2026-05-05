# 页面说明

## 书架页面 (BookshelfPage)

项目列表页面，展示用户的所有小说项目。

**路由**: `/`

**功能**:
- 展示项目卡片列表
- 创建新项目
- 删除项目
- 搜索筛选

## 章节页面 (Chapters)

核心章节编辑页面。

**路由**: `/project/:id/chapters`

**功能**:
- 章节列表展示
- 批量生成章节
- 章节内容编辑
- 章节重排序

**核心组件**:
- `ChapterList` - 章节列表
- `ChapterEditor` - 富文本编辑器
- `GenerationPanel` - AI 生成面板

## 角色管理页面 (Characters)

**路由**: `/project/:id/characters`

**功能**:
- 角色 CRUD
- 角色关系管理
- 角色属性配置

## 大纲页面 (Outline)

**路由**: `/project/:id/outline`

**功能**:
- 故事大纲编辑
- 章节规划
- 伏笔管理
