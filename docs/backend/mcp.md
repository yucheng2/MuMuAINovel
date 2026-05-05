# MCP 插件系统

## 概述

MCP (Model Context Protocol) 是一种扩展 AI 模型能力的协议，允许接入外部工具和数据源。

## 架构

```
┌─────────────┐     MCP      ┌─────────────┐
│   AI Model  │◄────────────►│  MCP Server │
└─────────────┘              └──────┬──────┘
                                    │
                             ┌──────▼──────┐
                             │   Plugin    │
                             │  (Python)   │
                             └─────────────┘
```

## 内置插件

### 1. Search Plugin
提供网络搜索能力。

### 2. Image Generation Plugin
图片生成功能。

## 开发插件

### 插件结构

```
mcp_plugins/
└── my_plugin/
    ├── __init__.py
    ├── plugin.py        # 插件主类
    └── manifest.json    # 插件配置
```

### 示例插件

```python
# plugin.py
from mcp_plugin import Plugin, Tool

class MyPlugin(Plugin):
    name = "my_plugin"
    version = "1.0.0"

    def get_tools(self):
        return [
            Tool(
                name="hello",
                description="打招呼",
                input_schema={"type": "object", "properties": {}}
            )
        ]

    async def execute(self, tool_name, arguments):
        if tool_name == "hello":
            return "你好！"
```

## 插件管理

在管理界面中可以：
- 查看已安装插件
- 启用/禁用插件
- 配置插件参数
