# 组件文档

## ChapterReader

章节阅读器组件，用于展示和编辑章节内容。

### 属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `content` | `string` | 章节内容 |
| `onSave` | `(content: string) => void` | 保存回调 |
| `readonly` | `boolean` | 是否只读模式 |

### 使用示例

```tsx
import { ChapterReader } from '@/components/ChapterReader'

<ChapterReader
  content={chapterContent}
  onSave={handleSave}
  readonly={false}
/>
```

---

## CharacterCard

角色卡片组件，展示角色信息。

### 属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `character` | `Character` | 角色数据 |
| `onEdit` | `(character: Character) => void` | 编辑回调 |
| `onDelete` | `(id: string) => void` | 删除回调 |

### 使用示例

```tsx
import { CharacterCard } from '@/components/CharacterCard'

<CharacterCard
  character={characterData}
  onEdit={handleEdit}
  onDelete={handleDelete}
/>
```

---

## RelationshipGraph

角色关系图谱组件，基于 @xyflow/react 实现。

### 属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `characters` | `Character[]` | 角色列表 |
| `relationships` | `Relationship[]` | 关系数据 |

### 使用示例

```tsx
import { RelationshipGraph } from '@/components/RelationshipGraph'

<RelationshipGraph
  characters={characterList}
  relationships={relationshipData}
/>
```
