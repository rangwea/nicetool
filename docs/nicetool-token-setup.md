# Token 配置

[返回文档索引](README.md)

## 通过安装脚本授权

[Skill 安装脚本](nicetool-skill.md)会打开浏览器，请求用户授权。确认后，凭据保存在 `${XDG_CONFIG_HOME:-$HOME/.config}/nicetool/credentials.env`，权限为 `0600`。客户端配置只保存实例地址和 Token 环境变量名。

## 手工配置

1. 登录目标实例。
2. 打开右上角用户菜单中的 Token 管理。
3. 创建个人 Token，立即保存完整值。
4. 为当前终端配置环境变量。

直接指定 Server 时：

```bash
export NICETOOL_TOKEN='replace-with-your-token'
uv run python plugins/nicetool/skills/nicetool/scripts/tool-cli.py   --server http://localhost:8000 list
```

使用命名环境时，变量名应与该环境配置中的 `token_env` 一致，例如 `NICETOOL_LOCAL_TOKEN`。环境变量只对当前终端及其子进程生效；编辑器或 Agent 需要从配置了变量的环境启动。

## 更新与撤销

Token 丢失后不能取回明文，应重新生成。撤销旧 Token 后，更新本地凭据或环境变量。不应将 Token 写进工具代码、客户端 TOML、提交记录或问题报告。

401 通常表示凭据无效，403 通常表示账号、项目或操作权限不足。更换 Token 不会自动增加账号权限。
