# 开发与贡献

[返回文档索引](README.md)

## 开发环境

```bash
uv sync --locked
uv run main.py
```

服务运行需要 MySQL；测试多使用模拟对象或 SQLite，但导入模块时可能尝试初始化 MySQL 数据源。

```bash
# 忽略工作目录 dotenv，运行测试
ENV_FILE=/dev/null uv run python -m unittest discover -s tests

# Ruff 当前不是项目依赖，使用 uvx 执行
uvx ruff check .
uvx ruff format --check .
```

上述环境变量写法适用于 POSIX Shell。已有代码可能存在格式问题，提交时区分原有问题和本次引入的问题。增加依赖使用 `uv add` 并一并提交 `pyproject.toml`、`uv.lock`，不维护 requirements.txt。

## 项目结构

| 目录 | 职责 |
| --- | --- |
| `core/` | 配置、认证、数据库连接、固定样式与共享运行能力 |
| `models/` | SQLModel 表与数据模型 |
| `service/` | 工具生命周期、存储、项目访问控制等业务逻辑 |
| `public/` | NiceGUI 页面与 FastAPI 路由 |
| `component/` | 共享 UI |
| `plugins/nicetool/` | 分发的 Skill、CLI 和参考资料 |
| `tests/` | 自动化测试 |
| `scripts/init.sql` | 当前完整建表定义 |

页面和 API 都可以调用服务层。数据库操作使用 `db_manager.session_scope()`；管理控制器继承 `BaseController` 并注册到后台入口。页面模块通过 `public/__init__.py` 导入以注册路由。

`tools/` 是运行缓存，不是版本存储。工具入口校验集中在 `service/tool_runtime.py`，元数据解析集中在 `service/tool_metadata.py`。新增行为应复用这些实现，避免再次引入兼容执行分支。

## 提交修改

1. 从维护中的分支创建工作分支，保持修改聚焦。
2. 为行为变化补充能复现问题的测试；文档修改检查链接与示例。
3. 同步受影响文档和 Skill 参考资料。
4. 修改表结构时更新模型和建表脚本，并说明已有数据库如何迁移。
5. 提交前检查 diff，移除真实凭据、日志和业务数据。
6. 在合并请求中描述问题、修改结果、验证步骤和已知限制。

Skill 的正式源是 `plugins/nicetool/skills/nicetool`，`.agents/skills/nicetool` 指向它，不需要维护两份副本。

## 报告问题

通过当前代码托管平台的问题跟踪入口报告。附上提交版本、操作系统、启动方式、复现步骤和脱敏错误日志。当前仓库没有公开仓库地址或许可证声明，文档不假设特定托管平台和贡献协议。
