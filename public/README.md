# NiceTool 公共模块

## 目录结构

```
public/
├── __init__.py          # 主模块导入
├── index.py             # 首页
├── admin/               # 管理员功能包
│   ├── __init__.py
│   ├── admin_dashboard.py      # 管理员控制台 (/admin)
│   ├── projects_management.py  # 项目管理 (/admin/projects)
│   └── tool_generator.py       # AI工具生成器 (/admin/tools/create)
└── user/                # 用户功能包
    ├── __init__.py
    ├── user_dashboard.py        # 用户首页 (/user)
    └── tools_handler.py         # 工具处理器 (/tools/{project}/{tool})
```

## 功能分类

### 管理员功能 (admin包)
- **admin_dashboard.py**: 管理员控制台，包含仪表盘、项目管理、工具管理、用户管理、系统设置等
- **projects_management.py**: 独立的项目管理页面，提供项目CRUD操作
- **tool_generator.py**: AI工具生成器，用于创建新工具

### 用户功能 (user包)
- **user_dashboard.py**: 用户首页，展示可用工具和项目
- **tools_handler.py**: 工具路由处理器，动态加载和执行项目工具

## 路由映射

| 路由 | 文件 | 功能 |
|------|------|------|
| `/` | index.py | 首页 |
| `/admin` | admin/admin_dashboard.py | 管理员控制台 |
| `/admin/projects` | admin/projects_management.py | 项目管理 |
| `/admin/tools/create` | admin/tool_generator.py | AI工具生成器 |
| `/user` | user/user_dashboard.py | 用户首页 |
| `/tools/{project}/{tool}` | user/tools_handler.py | 工具执行 |

## 使用方式

在应用启动时导入所有模块：

```python
from public import *
```

这将自动注册所有路由和页面处理器。
