# 前端文档

基于 React 18 + TypeScript 构建的单页应用。

## 技术栈

- React 18 + TypeScript
- Vite 7 - 构建工具
- Ant Design 5 - UI 组件库
- Zustand 5 - 状态管理
- React Router DOM 6 - 路由
- @xyflow/react - 流程图/关系图

## 项目结构

```
frontend/src/
├── pages/           # 页面组件
│   ├── BookshelfPage.tsx   # 书架
│   ├── Chapters.tsx         # 章节编辑
│   ├── Characters.tsx       # 角色管理
│   └── ...
├── components/      # 通用组件
├── services/        # API 调用
└── store/           # 状态管理
```

---

## 组件文档

### ChapterReader

章节阅读器组件，用于展示和编辑章节内容。

```tsx
import { ChapterReader } from '@/components/ChapterReader'

<ChapterReader
  content={chapterContent}
  onSave={handleSave}
  readonly={false}
/>
```

### CharacterCard

角色卡片组件，展示角色信息。

```tsx
import { CharacterCard } from '@/components/CharacterCard'

<CharacterCard
  character={characterData}
  onEdit={handleEdit}
  onDelete={handleDelete}
/>
```

### RelationshipGraph

角色关系图谱组件。

```tsx
import { RelationshipGraph } from '@/components/RelationshipGraph'

<RelationshipGraph
  characters={characterList}
  relationships={relationshipData}
/>
```
