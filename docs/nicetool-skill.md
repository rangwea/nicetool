# CLI 与 Skill

[返回文档索引](README.md)

CLI 位于 `plugins/nicetool/skills/nicetool/scripts/tool-cli.py`。本仓库使用 `uv run python` 执行；Skill 正式源位于 `plugins/nicetool/skills/nicetool`，项目内 `.agents/skills/nicetool` 是符号链接。

## 从实例安装 Skill

先由管理员在环境管理中设置启用环境及默认环境。确认实例可信后，在目标项目目录执行：

```bash
curl -fsSL https://tools.example.com/api/install.sh | sh
```

安装脚本下载 Skill、初始化客户端配置，并打开浏览器请求授权。默认可交互选择安装到当前项目或全局目录；无交互环境使用 `--local` 或 `--global`。参数 `--target /path/to/project` 指定项目；`--force` 替换已有 Skill；`--skip-auth` 跳过浏览器授权。已有客户端配置保留。

```bash
# 安装到当前项目
curl -fsSL https://tools.example.com/api/install.sh | sh -s -- --local

# 安装到用户级全局目录
curl -fsSL https://tools.example.com/api/install.sh | sh -s -- --global
```

```bash
curl -fsSL https://tools.example.com/api/install.sh   | sh -s -- --target /path/to/project --skip-auth
```

也可手动复制完整的 `plugins/nicetool/skills/nicetool` 目录到 Agent 支持的 Skill 搜索目录。保留其中的脚本和参考资料，不要只复制 `SKILL.md`。

## 连接实例

直接使用仓库中的 CLI：

```bash
export NICETOOL_TOKEN='replace-with-your-token'
uv run python plugins/nicetool/skills/nicetool/scripts/tool-cli.py   --server http://localhost:8000 list
```

已安装到目标项目时，将脚本路径换为 `.agents/skills/nicetool/scripts/tool-cli.py`。

多实例可执行 `/api/init.sh` 初始化配置，然后通过 `--env <名称>` 选择环境，或用 `--config <路径>` 指定 TOML。环境名称、URL、`token_env` 来自后台环境管理，不固定为 test/prod。

## 开发流程

以下命令在仓库根目录执行。远端操作复用同一 Server 地址；启用认证时需要先配置 Token。

```bash
# 只创建本地文件
uv run python plugins/nicetool/skills/nicetool/scripts/tool-cli.py create demo hello

# 创建固定预览
uv run python plugins/nicetool/skills/nicetool/scripts/tool-cli.py   --server http://localhost:8000 preview demo hello --file tools/demo/hello.py

# 查看预览日志
uv run python plugins/nicetool/skills/nicetool/scripts/tool-cli.py   --server http://localhost:8000 prelog demo hello

# 上传并发布正式版本
uv run python plugins/nicetool/skills/nicetool/scripts/tool-cli.py   --server http://localhost:8000 publish demo hello --file tools/demo/hello.py

# 查询正式状态
uv run python plugins/nicetool/skills/nicetool/scripts/tool-cli.py   --server http://localhost:8000 status demo hello
```

发布需要相应操作权限。`create` 不调用服务端；`preview` 不更新正式版本，但会执行工具代码；`publish` 写入正式源码版本。

## 常用命令

| 命令 | 用途 |
| --- | --- |
| `list` / `projects` | 列出可访问的工具或项目 |
| `get <project> <name>` | 读取工具详情 |
| `create <project> <name>` | 本地生成工具 |
| `preview --file <path>` | 临时预览 |
| `publish <project> <name> --file <path>` | 上传并发布 |
| `status <project> <name>` | 正式状态 |
| `toollog` / `prelog` | 正式日志 / 预览日志 |
| `databases` / `variables` | 查看可用配置元信息 |
| `delete <project> <name>` | 删除正式工具 |

全局参数放在子命令前。完整参数通过 `--help` 或 `<命令> --help` 查看。删除和发布前确认实例、项目及文件名；Agent 的操作还应遵守所安装 Skill 的授权规则。
