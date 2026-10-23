# API 导航

[返回文档索引](README.md)

启动服务后，通过 `/docs` 查看 Swagger，`/redoc` 查看 ReDoc，`/openapi.json` 获取接口 Schema。子路径部署时添加 `PROJECT_PATH`。请求字段、响应结构与错误码以运行实例的 Schema 和实现为准。

## 接口分组

| 路径 | 用途 | 源码 |
| --- | --- | --- |
| `/api/tools` | 工具列表、详情、预览、发布、状态、日志和删除 | `public/api/tool_api.py` |
| `/api/datasources` | 数据源查询与连接测试 | `public/api/datasource_api.py` |
| `/api/variables` | 平台变量 Key 列表 | `public/api/variable_api.py` |
| `/auth` | 登录、账号初始化、个人 Token 和设备授权 | `public/api/auth_api.py` |
| `/api/init.sh`、`/api/install.sh` | 客户端初始化与安装 | `public/init_script.py` |
| `/api/downloads` | Skill ZIP 下载 | `public/skill_download.py` |
| `/health` | 健康检查 | `public/api/health_api.py` |

不是所有后台操作都有对应 REST CRUD 接口。枚举、用户项目授权等后台功能可直接调用服务层；不要推断未声明的端点。

## 读取工具

```bash
curl --fail-with-body http://localhost:8000/api/tools   -H "Authorization: Bearer $NICETOOL_TOKEN"
```

启用认证时，Token 和账号状态参与访问检查；工具列表受项目授权限制。

## 上传并发布

```bash
uv run python -c 'import json; from pathlib import Path; print(json.dumps({"content": Path("hello.py").read_text()}))'   | curl --fail-with-body -X POST http://localhost:8000/api/tools/demo/hello/publish       -H "Authorization: Bearer $NICETOOL_TOKEN"       -H 'Content-Type: application/json' --data-binary @-
```

该操作写入正式版本，需要发布权限。建议先用 CLI 预览。临时预览端点为 `POST /api/tools/preview`，同样接收包含 `content` 的 JSON。

## 访问与集成边界

普通页面通过 Cookie 登录，CLI 使用 Bearer Token。预览 URL 默认处于公共路径范围，不应将其当作私有数据隔离机制。对接时同时核对路径保护、项目授权与操作 scope；参见[认证说明](oauth2-auth.md)。

## 工具名称与源码契约

项目名和工具名仅允许小写字母、数字、下划线和连字符；项目名最长 100 个字符，工具名最长 197 个字符。工具名不包含 `.py`。平台不会自动转小写、替换空格或剥离扩展名；非法名称会被拒绝，API 返回 HTTP 422。工具标题可使用中文，与工具标识符分开。

发布必须上传包含顶层 `main()` 的 Python 源码。`POST /api/tools/{project}/{name}/publish` 必须携带 JSON 请求体 `{"content": "..."}`；缺失请求体、缺失 content 或空字符串返回 HTTP 422。源码语法或入口错误返回 HTTP 400。CLI 默认读取本地 `tools/{project}/{name}.py` 并上传，也可使用 `--file` 或 `--stdin`。服务端不会从当前数据库版本或本地运行缓存推断待发布内容。

MySQL 保存正式源码和版本，本地 `tools/` 仅作为可恢复的运行缓存。恢复历史源码请在后台使用版本回滚，它会创建新版本。工具详情不返回 revision，CLI `get --output` 仅写入源码文件；平台未提供乐观锁冲突保护。
