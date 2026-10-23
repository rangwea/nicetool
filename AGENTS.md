# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## 常用命令

```bash
# 安装依赖 (Python >= 3.13 required)
uv sync

# 启动应用
uv run main.py
# 或
uv run python main.py

# 代码检查
ruff check

# 自动修复代码问题
ruff check --fix

# 代码格式化
ruff format
```

## 访问地址

- **Web UI 首页**: http://localhost:8000
- **工具中心**: http://localhost:8000/user
- **管理后台**: http://localhost:8000/admin
- **API 文档 (Swagger)**: http://localhost:8000/docs
- **API 文档 (ReDoc)**: http://localhost:8000/redoc

## 项目架构

### 技术栈

| 组件 | 说明 |
|------|------|
| Python >= 3.13 | 运行环境 |
| NiceGUI >= 3.11 | Web UI 框架（基于 Quasar/Vue.js） |
| FastAPI + Uvicorn | RESTful API 后端 |
| SQLModel | ORM（基于 SQLAlchemy + Pydantic） |
| MySQL | 主数据库 |
| pydantic-settings | 配置管理（读取 `.env`） |
| loguru | 结构化日志 |
| ruff | 代码检查和格式化 |
| uv | 包管理和虚拟环境 |

### 核心目录结构

```
├── main.py                    # 应用入口：初始化 FastAPI + NiceGUI，注册路由
├── core/                      # 核心功能模块
│   ├── database.py            # DatabaseManager - 数据库连接池和会话管理
│   ├── datasource_manager.py  # 多数据源管理（MySQL/MongoDB），db['name'] 代理
│   ├── settings.py            # Settings(BaseSettings) 配置管理
│   ├── theme.py               # 6 主题系统（default/blue/green/purple/orange/dark）
│   ├── logger.py              # loguru 日志配置，支持按工具/预览隔离日志
│   └── error_handler.py       # @handle_service_errors 装饰器
├── models/                    # SQLModel 数据模型
│   ├── tool.py                # Tool（tools 表，project 为工具分组字段）+ ToolCreate/ToolUpdate/ToolResponse
│   └── datasource.py          # DataSource（datasources 表，统一 MySQL/MongoDB）
├── service/                   # 业务逻辑层（纯函数风格）
│   ├── tool_service.py        # 正式工具定位与动态加载
│   ├── tool_runtime.py        # 工具 main() 入口校验与加载
│   ├── tool_manage_service.py # 工具文件 CRUD（filesystem）
│   ├── datasource_service.py  # 数据源 CRUD
│   └── tool_version_service.py# 工具版本管理
├── public/                    # 页面控制器和 API 路由
│   ├── __init__.py            # 导入所有页面模块以触发路由注册
│   ├── index.py               # 首页 / (NiceGUI 页面)
│   ├── admin/                 # 管理后台页面控制器
│   │   ├── base_controller.py # BaseController 抽象基类 + Menu dataclass
│   │   ├── index.py           # /admin 页面，注册所有控制器
│   │   ├── datasource.py      # 数据源管理控制器
│   │   ├── preview_log.py     # 预览日志查看控制器
│   │   └── settings.py        # 系统设置控制器
│   ├── api/                   # FastAPI RESTful 路由
│   │   ├── tool_api.py        # /api/tools - 工具管理 + 预览
│   │   └── datasource_api.py  # /api/datasources - 数据源管理
│   ├── user/                  # 用户功能页面
│   │   ├── index.py           # /user - 工具浏览（搜索+筛选+网格）
│   │   └── tools.py           # /user/tools/{project}/{tool} - 工具执行
│   └── client/                # 客户端接口
│       └── preview.py         # /client/tool/{token} - 临时工具预览
├── component/                 # 可复用 UI 组件
├── tools/                     # 工具脚本目录（按项目子目录组织）
│   └── demo/
│       └── hello.py           # 示例工具
├── agent/                     # AI Agent 相关（commands, skills）
├── scripts/                   # CLI 脚本（tool-cli.py 等）
└── docs/                      # 文档目录
```

## 分层架构

```
表现层 (public/admin/ + public/user/)
    ↓
API 层 (public/api/)
    ↓
业务层 (service/)
    ↓
数据访问层 (core/database.py)
    ↓
数据库 (MySQL)
```

## 关键模式和约定

### 数据库操作

始终使用 `session_scope()` 上下文管理器，它自动处理 commit 和 rollback：

```python
from core.database import db_manager
from sqlmodel import select

with db_manager.session_scope() as session:
    statement = select(Model).where(Model.field == value)
    results = session.exec(statement).all()
    # commit 自动执行，异常时自动 rollback
```

### 管理后台控制器模式

所有管理页面控制器继承 `BaseController`，实现 `menu()` 和 `render()`：

```python
from public.admin.base_controller import BaseController, Menu


class MyController(BaseController):
    def menu(self) -> Menu:
        return Menu(icon="settings", label="模块名称", color="primary")

    def render(self):
        # 渲染页面内容
        with ui.column().classes("w-full gap-4"):
            ui.label("内容")


my_controller = MyController()

# 在 public/admin/index.py 的 controllers 列表中注册：
# controllers = [..., my_controller]
```

### FastAPI API 路由模式

```python
from fastapi import APIRouter
from core.database import db_manager

router = APIRouter(prefix="/api/xxx", tags=["xxx"])


@router.get("/")
def list_items():
    with db_manager.session_scope() as session:
        # 业务逻辑
        pass


# 在 main.py 中注册：
# fapp.include_router(xxx_api_router)
```

### NiceGUI UI 开发规范

- **避免内联样式**：使用 `.classes()` (Tailwind CSS) 和 `.props()` (Quasar props) 替代 `.style()`
- **可刷新组件**：使用 `@ui.refreshable` 实现局部刷新，避免重新渲染整个页面
- **表格自定义列**：使用 `table.add_slot('body-cell-{column_name}', ...)` 渲染自定义列

```python
@ui.refreshable
def render_table():
    table = ui.table(columns=columns, rows=rows, row_key="id")
    table.add_slot(
        "body-cell-actions",
        """
        <q-td :props="props">
            <q-btn icon="edit" @click="$parent.$emit('edit', props.row)" />
        </q-td>
    """,
    )
    table.on("edit", lambda e: handle_edit(e.args))
```

- **NiceGUI + FastAPI 混合架构**：`ui.run_with(fapp, ...)` 将 NiceGUI 挂载到 FastAPI，路由注册通过 `@ui.page()` 装饰器完成，路由所在模块必须在 `public/__init__.py` 中导入
- **NiceGUI 路由注册**：`import public` 在 `main.py` 中触发 `public/__init__.py` 的导入，从而注册所有 `@ui.page()` 路由

### 错误处理装饰器

```python
from core.error_handler import handle_service_errors


@ui.page("/my/page")
@handle_service_errors("页面加载失败")
def my_page():
    # 如果抛出异常，自动 ui.notify(..., type="negative") 并记录日志
    pass
```

### 日志使用

```python
from core.logger import get_logger

logger = get_logger(__name__)

logger.info("操作成功")
logger.warning("警告信息")
logger.error("错误信息")
logger.exception("带堆栈的错误")  # 自动包含 traceback
```

工具专属日志（写入 `logs/tools/{project}/{tool}/tool.log`）：

```python
from core.logger import get_tool_logger, tool_log_context

with tool_log_context(project_name, tool_name):
    tool_func()  # 此上下文中的 loguru 日志写入工具专属日志文件
```

## 新增后台管理模块流程

1. **创建数据模型** (`models/xxx_model.py`) — 继承 `SQLModel, table=True`
2. **实现服务层** (`service/xxx_service.py`) — 使用 `db_manager.session_scope()`
3. **创建 API 路由** (`public/api/xxx_api.py`) — 定义 RESTful 接口，在 `main.py` 注册
4. **创建控制器** (`public/admin/xxx.py`) — 继承 `BaseController`
5. **注册控制器** — 在 `public/admin/index.py` 的 `controllers` 列表中添加

## 环境变量（`.env` 文件）

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `HOST` | 监听地址 | `0.0.0.0` |
| `PORT` | 监听端口 | `8000` |
| `DEBUG` | 调试模式 | `false` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `MYSQL_HOST` | MySQL 主机 | — |
| `MYSQL_PORT` | MySQL 端口 | — |
| `MYSQL_USER` | MySQL 用户 | — |
| `MYSQL_PASSWORD` | MySQL 密码 | — |
| `MYSQL_DATABASE` | MySQL 数据库名 | — |
| `STORAGE_SECRET` | NiceGUI 存储密钥 | — |
| `PROJECT_PATH` | 应用及 NiceGUI 挂载路径 | — |
| `LANGUAGE` | 平台界面语言 | `zh-CN` |
| `TOOLS_DIR` | 工具目录绝对路径 | — |

## 样式系统

`apply_app_styles()` 在 `main.py` 启动时调用，固定配置默认品牌色、全局 CSS
变量及 NiceGUI 组件默认样式。项目不提供主题切换或主题偏好持久化。

## 日志文件位置

| 日志文件 | 说明 |
|----------|------|
| `logs/app.log` | 应用全局日志（轮转）|
| `logs/error.log` | 仅错误日志 |
| `logs/tools/{project}/{tool}/tool.log` | 工具专属日志 |
| `/tmp/nicegui_client_tools/_logs/{token}.log` | 预览工具执行日志 |

## Docker 部署

```bash
# 构建环境镜像
docker build --platform linux/amd64 -t nicetool-env -f Dockerfile.env .

# 运行（挂载源码，带环境变量）
docker run -d -p 8000:8000 -v $(pwd):/app --env-file .env --name nicetool-dev nicetool-env

# 访问宿主机服务（如本地 MySQL/MongoDB）
docker run -d -p 8000:8000 -v $(pwd):/app --env-file .env \
  --add-host=host.docker.internal:host-gateway --name nicetool-dev nicetool-env
```

## 数据库 Schema

主要表：`tools`、`datasources`、`tool_drafts`、`tool_chat_history`

初始化 DDL 脚本：`scripts/init.sql`（仅包含当前完整表结构，不使用数据库外键）

`main.py` 启动时会调用 `db_manager.create_tables()` 自动创建 SQLModel 定义的表。
