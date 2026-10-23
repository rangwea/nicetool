# NiceTool

一站式 AI 工具平台，让想法成为团队可用的工具。

用自然语言描述需求，让 AI 创建工具，在浏览器中预览验证，再发布到团队的工具中心。NiceTool 将数据接入、工具生成、预览调试、发布共享、版本管理和访问授权串成完整流程，让工具从一次性的需求变成可以持续使用和改进的团队资源。

使用者只需关注要解决什么问题、结果是否正确，无需了解工具的底层语言。创建者通过接入 NiceTool Skill 的 AI 编程助手描述需求、调整功能；团队成员通过浏览器直接使用已发布的工具。

## 从需求到可用工具

1. **描述需求**：告诉 AI 需要查询哪些数据、完成什么操作、如何展示结果。
2. **生成工具**：AI 结合项目上下文、已配置的数据源和开发规范创建工具。
3. **预览调整**：打开预览页面验证效果，继续用自然语言提出修改；AI 可读取日志排查问题。
4. **发布共享**：确认结果后发布到工具中心，为需要的成员分配项目访问权限。
5. **持续改进**：根据反馈迭代工具，通过版本和日志管理后续维护。

AI 创建和修改工具通过外部 AI 编程助手与 Skill 完成；NiceTool 提供工具运行、预览、发布及团队管理服务。

## 可以用 NiceTool 做什么

| 场景 | 示例 |
| --- | --- |
| 数据查询 | 按订单号、状态和日期筛选记录，查看分页明细 |
| 业务操作 | 创建信息维护表单、批量处理和日常管理工具 |
| 统计分析 | 汇总业务指标，生成趋势图、分析面板和导出报表 |
| 团队协作 | 集中发布工具，按项目授权，让成员通过统一入口使用 |

## 平台能力

- **AI 驱动创建**：通过 NiceTool Skill 将自然语言需求转化为工具，支持连续修改和调试。
- **完整发布流程**：从预览验证到正式发布，提供版本记录、回滚和日志查看。
- **统一工具中心**：按项目组织工具，支持浏览、搜索、筛选和直接运行。
- **共享数据能力**：集中管理 MySQL、MongoDB 数据源、平台变量和枚举，供工具复用。
- **团队访问管理**：支持内置账号、OIDC/OAuth2、个人 Token 和用户项目授权。
- **只读分析能力**：NiceTool Skill 支持数据查询、图表、仪表盘及有数量上限的导出。

## 一键体验

只需 Docker 和 Compose v2，即可启动包含合成数据的完整演示：

```bash
sh scripts/demo.sh
```

打开 [工具中心](http://localhost:8000/user)，体验订单查询、销售看板和报价计算器。无需安装 Python、准备数据库或配置模型密钥。

接着按[完整 AI 创建示例](docs/demo.md)让你的 AI 助手创建新工具、根据反馈修改并发布。演示仅允许本机访问，全部数据均为合成数据。

## 创建你的第一个 AI 工具

已有 NiceTool 实例时，先在工作项目中[安装 NiceTool Skill](docs/nicetool-skill.md)并完成账号授权，再向支持 Skill 的 AI 编程助手描述需求：

> 创建一个订单查询工具，使用已配置的订单数据源，支持按订单号、日期和状态筛选，分页展示结果。先生成预览，不发布。

打开 AI 返回的预览地址，验证后继续调整：

> 增加订单金额汇总，并支持导出当前筛选结果，最多导出 1000 条。

确认效果和目标实例后发布：

> 将已验证的工具发布到订单项目，并核对正式状态。

管理员为成员分配项目访问权限后，成员即可从工具中心打开使用。普通使用者无需安装开发环境，也无需编写代码。发布需要相应权限；更多示例见[开发任务示例](docs/nicetool-skill-usage.md)。

## 部署自己的平台

准备 Python 3.13+、uv 和一个可访问的 MySQL 实例。下载本仓库后，在仓库根目录执行：

```bash
uv sync --locked
```

先在 MySQL 中创建数据库，为应用账号授予该数据库的建表和读写权限：

```sql
CREATE DATABASE nicetool CHARACTER SET utf8mb4;
```

参考 `.env.example` 创建或编辑根目录 `.env`，将以下示例值替换为本地配置；已有 `.env` 时先备份，不直接覆盖：

```dotenv
HOST=0.0.0.0
PORT=8000
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=nicetool
MYSQL_PASSWORD=replace-with-your-password
MYSQL_DATABASE=nicetool
STORAGE_SECRET=replace-with-a-random-secret
AUTH_ENABLED=true
AUTH_JWT_SECRET=replace-with-another-random-secret
```

可用 `uv run python -c "import secrets; print(secrets.token_urlsafe(32))"` 生成密钥。不要将实际凭据提交到版本控制。

```bash
uv run main.py
```

启动时创建缺失的数据表，并从数据库恢复工具缓存。访问 [登录页](http://localhost:8000/auth/login)初始化管理员，再进入[管理后台](http://localhost:8000/admin)配置用户和数据源。

| 入口 | 默认地址 |
| --- | --- |
| 首页 | <http://localhost:8000> |
| 工具中心 | <http://localhost:8000/user> |
| 管理后台 | <http://localhost:8000/admin> |
| API 文档 | <http://localhost:8000/docs> |
| 健康检查 | <http://localhost:8000/health> |

### Docker 部署

```bash
docker build -t nicetool .
docker run -d --name nicetool --env-file .env -p 8000:8000 nicetool
```

镜像包含平台运行环境，通过 uv 按 `uv.lock` 安装依赖。容器内的 `MYSQL_HOST` 必须指向容器可访问的数据库地址。镜像排除 `.env` 和环境专用配置，运行时通过环境变量注入。持久化、反向代理及升级说明见[部署指南](docs/deployment.md)。

## 文档

从[文档索引](docs/README.md)选择你的使用路径：

- [配置参考](docs/configuration.md)
- [用户与管理员指南](docs/user-guide.md)
- [认证与项目权限](docs/oauth2-auth.md)
- [工具开发](docs/tool-development.md)
- [CLI 与 Skill](docs/nicetool-skill.md)
- [API 导航](docs/api.md)
- [开发与贡献](docs/contributing.md)

## 开发者说明

平台底层采用 Python、NiceGUI、FastAPI 和 MySQL。工具源码版本保存在数据库中，`tools/` 是可重建的运行缓存；工具代码在服务进程内执行，因此发布权限应授予可信开发者。

需要手工开发工具、扩展平台或集成 API 时，请参阅[工具开发](docs/tool-development.md)、[API 导航](docs/api.md)和[贡献指南](docs/contributing.md)。

## 参与贡献

欢迎提交问题报告、文档改进和聚焦的代码修改。报告问题时提供复现步骤、版本和脱敏日志；行为变更请附测试及迁移说明。项目使用 uv 管理依赖，具体命令见[贡献指南](docs/contributing.md)。

## 许可证

当前仓库未提供 `LICENSE` 文件，许可证尚未声明。
