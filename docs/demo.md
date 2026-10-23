# 先体验：AI 可以帮你创建什么

只需 Docker 和 Compose v2，不需要安装 Python、准备数据库或配置模型密钥。先体验三个成品工具，再让你使用的 AI 助手继续修改。

## 一键启动

在仓库根目录执行：

```bash
sh scripts/demo.sh
```

英文界面请在 `.env` 文件中设置 `LANGUAGE=en-US`，再运行 `sh scripts/demo.sh`。

首次启动需要网络下载镜像与依赖。脚本等待数据库和平台就绪后，输出工具中心地址：

[打开演示工具中心](http://localhost:8000/user)

端口被占用时：

```bash
DEMO_PORT=8080 sh scripts/demo.sh
```

演示独立使用 `nicetool_demo` 数据库和 Docker 卷；`.env` 中的语言配置用于界面，数据库连接和认证使用固定的演示配置。默认关闭登录，只绑定 `127.0.0.1`。它用于本机体验，不是正式部署配置，也不适合通过代理暴露到公网。

## 三个可直接使用的工具

| 工具 | 试一试 | 应看到的结果 |
| --- | --- | --- |
| [订单查询](http://localhost:8000/user/tools/demo/order_query) | 输入 `DEMO-001` 后查询 | 一条示例客户订单；支持分页与 CSV 导出 |
| [销售看板](http://localhost:8000/user/tools/demo/sales_dashboard) | 查看指标及六个月趋势 | 60 条订单、20 条已完成订单；销售额只统计已完成订单 |
| [报价计算器](http://localhost:8000/user/tools/demo/quote_calculator) | 数量 10、单价 99、折扣 10% | 报价 891.00 元；不保存任何业务数据 |

全部订单为固定合成数据，来源是 `examples/demo/orders.csv`。无需连接真实业务系统。三个工具是预置示例，不表示平台已在后台调用模型生成；修改和生成需要你的外部 AI 助手。

## 让 AI 修改一个工具

在支持项目 Skill 的 AI 编程助手中打开本仓库。仓库已经包含 NiceTool Skill；若工具未自动发现它，可明确要求读取 `plugins/nicetool/skills/nicetool/SKILL.md`。

给 AI 以下任务：

> 使用 NiceTool Skill，基于当前演示项目创建一个新工具 demo/order_analysis。参考 examples/demo/tools/order_query.py，读取 examples/demo/orders.csv，支持订单状态筛选，显示订单数量和已完成订单金额。不要修改现有三个演示工具。目标实例是 http://localhost:8000，先预览，不发布。

业务口径见 [演示数据说明](../examples/demo/README.md)。若使用了其他端口，请同步替换任务中的实例地址。

验证预览后继续：

> 增加按月汇总图表。金额只统计已完成订单，取消订单不计入，保留无订单月份的展示。修改后重新预览，并说明你验证了哪些输入和结果。

确认结果后发布：

> 将这次已验证的候选源码发布到本机演示实例的 demo/order_analysis，并核对正式页面和版本。

演示实例关闭鉴权，不需要个人 Token，也不需要浏览器授权。若要把 Skill 安装到另一个业务项目，安装时使用 `--skip-auth`；这些示例依赖本仓库的 `examples.demo.data`，因此本教程应在当前仓库内完成。

## 停止、重启和重置

停止并保留数据库和修改：

```bash
docker compose --env-file /dev/null -f compose.demo.yaml down
```

再次运行 `sh scripts/demo.sh` 即可启动。初始化只补充不存在的示例工具，不覆盖已有版本；已删除的预置示例会在下次启动时重新创建。默认客户端环境仅在列表为空时创建，已有配置保留。

完全删除演示数据库、工具修改、日志及预览，再从头体验：

```bash
# 破坏性操作，仅在确定不要现有演示内容时执行。
docker compose --env-file /dev/null -f compose.demo.yaml down --volumes
sh scripts/demo.sh
```

## 排查启动问题

```bash
docker compose --env-file /dev/null -f compose.demo.yaml ps
docker compose --env-file /dev/null -f compose.demo.yaml logs --tail 80 app db
```

本机有 Python 时，可运行脱敏诊断：

```bash
python3 scripts/doctor.py --server http://localhost:8000
```

成功退出码为 0，检查失败为 1。诊断不读取 `.env`，不输出 Token、数据库密码或 HTTP 响应正文。健康接口仅表示 HTTP 服务存活，不能替代数据库与工具功能验收。

正式使用请阅读[部署指南](deployment.md)，从 `.env.example` 配置自己的数据库和登录密钥。
