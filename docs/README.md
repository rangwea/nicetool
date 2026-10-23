# NiceTool 文档

本文档描述当前仓库实现。示例使用本机地址或 `example.com`，不依赖特定组织的部署环境。

## 部署和使用

首次体验从[一键演示与 AI 创建教程](demo.md)开始。升级现有实例见[升级与恢复](upgrading.md)。

| 目标 | 文档 |
| --- | --- |
| 安装并运行 | [README](../README.md) |
| 容器、反向代理、升级和备份 | [部署指南](deployment.md) |
| 界面语言与翻译扩展 | [国际化](internationalization.md) |
| 配置环境变量 | [配置参考](configuration.md) |
| 浏览工具、管理用户和数据源 | [用户指南](user-guide.md) |
| 登录、Token 与项目访问授权 | [认证与权限](oauth2-auth.md) · [Token 配置](nicetool-token-setup.md) |

## 开发和集成

| 目标 | 文档 |
| --- | --- |
| 编写 Python 工具 | [工具开发](tool-development.md) |
| 安装 Skill、使用 CLI | [CLI 与 Skill](nicetool-skill.md) |
| 给开发助手描述任务 | [任务示例](nicetool-skill-usage.md) |
| 创建只读统计和图表 | [CLI 与 Skill](nicetool-skill.md) |
| 调用 HTTP 接口 | [API 导航](api.md) |
| 修改平台并贡献代码 | [贡献指南](contributing.md) |

`plans/` 保存历史设计记录，不作为当前配置或接口契约。实际行为以源码和运行实例的 OpenAPI 文档为准。
