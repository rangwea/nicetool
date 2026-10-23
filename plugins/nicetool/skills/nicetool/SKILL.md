---
name: nicetool
description: 创建、修改、预览调试和发布单文件 NiceTool 工具，查询平台资源或初始化客户端。配置、变量、数据源和枚举请求仅在 NiceTool 工具上下文中触发。
---

# NiceTool

## 执行入口

以本次加载的 skill 目录为 `NICETOOL_SKILL_ROOT`，使用绝对路径且保持用户工作目录。
不要假定工作区有 `.agents/skills/nicetool`。CLI 仅依赖标准库，需要 Python 3.11+；工具运行环境为 Python 3.13+。

```bash
python3 "$NICETOOL_SKILL_ROOT/scripts/tool-cli.py" --json <command>
python3 "$NICETOOL_SKILL_ROOT/scripts/validate-tool.py" <file>
```

命令：`list projects get create preview prelog publish status delete databases variables toollog`。
正式工具 project/name 仅支持小写字母、数字、下划线和连字符，长度上限分别为 100/197，name 不带 `.py`；非法名称直接修正输入，不依赖服务端自动转换。
`variables` 仅返回 Key 和备注；`toollog` 读取本机日志且输出文本，不查询远端环境。

## Agent loop

维护最小任务状态：目标 `project/name`、本地文件、环境、已授权动作、当前阶段及最近错误。
只在目标或环境真正不明时询问；`project` 默认当前目录名，`name` 使用英文 snake_case。

1. **定位**：已有本地文件直接修改；修改目标缺失时才 `get project name --output <file>`。
   新建直接写 `tools/<project>/<name>.py` 或用本地 `create`，不先查询远端。
   同名冲突且覆盖意图不明时澄清；明确修改已有目标无需再确认。
2. **编辑 → 校验**：按下表加载所需参考，运行静态校验；根据具体错误修复，再校验。
   校验通过且只要求生成/修改时交付，不强制预览。
3. **预览 → 观察 → 修复**：要求预览、验证或报告运行错误时，加载
   [lifecycle.md](references/lifecycle.md) 执行闭环。每次修改后先校验再更新预览。
4. **正式动作**：发布、部署、上线统一使用 `publish`；删除使用 `delete`。
   执行前加载生命周期参考，沿用会话中针对目标与环境的授权。预览不授权发布或业务写入。
5. **结束**：达到请求的验证阶段即交付；无新证据时不重放相同操作。
   缺配置、权限或外部依赖时报告所需输入。正式写入结果不明时先只读核实，不能盲目重试。

## 按需加载

已读且未变的参考不重复读取；只改逻辑不加载视觉文档，不重套模板。

| 当前工作 | 读取 |
|---|---|
| 所有代码生成/修改 | [quality-gate.md](references/quality-gate.md) |
| 新建或调整 UI | [design.md](references/design.md)；需要选择构图时才读 [design-scenes.md](references/design-scenes.md) 对应章节 |
| 新建工具模板（二选一） | 简单表单：[simple-tool.py](references/simple-tool.py)；筛选分页详情：[query-tool.py](references/query-tool.py) |
| 数据库访问 | [datasources.md](references/datasources.md) |
| 平台变量 / 托管枚举 | [variables.md](references/variables.md) / [uix.md](references/uix.md) |
| 预览调试、发布、删除 | [lifecycle.md](references/lifecycle.md) |
| 初始化、环境选择或生产操作 | [environments.md](references/environments.md) |
| 自定义复杂布局/组件 | [design-details.md](references/design-details.md) 对应章节 |
| 技能行为评测 | [forward-tests.md](references/forward-tests.md) |

仅遇到对应 NiceGUI API 问题时加载：
[入口](references/nicegui/01-foundations.md)、[输入事件](references/nicegui/02-inputs-events-validation.md)、
[布局](references/nicegui/03-layout-styling-responsive.md)、[状态刷新](references/nicegui/04-state-binding-refresh.md)、
[表格图表](references/nicegui/05-data-display-charts.md)、[异步隔离](references/nicegui/06-async-tasks-multi-user.md)、
[弹窗文件](references/nicegui/07-feedback-dialogs-files.md)、[互操作测试](references/nicegui/08-security-testing-interop.md)。

## 交付

对用户称 NiceTool。只报告已完成的阶段：文件、静态检查、预览链接、页面/交互验证、正式发布。
静态检查不执行源码；预览上传成功不证明页面正常。给出结果、验证和实际阻塞点，不粘贴完整源码或日志。
