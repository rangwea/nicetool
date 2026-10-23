# NiceTool 平台变量

当工具需要读取后台“变量管理”中的全局字符串配置时加载本文件。

## 读取接口

只通过只读代理访问变量：

```python
from core.variable_manager import variables

api_base = variables["API_BASE"]
timeout_text = variables.get("REQUEST_TIMEOUT", "30")
```

- `variables["KEY"]`：变量不存在时抛出 `KeyError`，用于缺失配置应阻止工具运行的场景。
- `variables.get("KEY", default)`：变量不存在时返回默认值，用于业务上确实允许回退的场景。
- 每次读取都查询平台数据库，不缓存；后台修改会在下一次读取时生效。
- `value` 始终是字符串，空字符串与变量不存在不同。

不要直接导入 `models.variable`、`service.variable_service` 或数据库表，也不要给只读代理增加写入行为。

## 选择正确的配置来源

| 需求 | 使用方式 |
|---|---|
| 管理员可在后台修改的全局字符串配置 | `core.variable_manager.variables` |
| MySQL/MongoDB 连接 | `core.datasource_manager.db` |
| 工具自身固定且不需要后台修改的选项 | 单文件常量或 NiceGUI 控件 |
| 平台托管枚举 | `core.uix.enums_select` |

生成工具前需要发现可用 Key 时，使用只读 CLI：

按 `SKILL.md` 将 `NICETOOL_SKILL_ROOT` 设为实际 skill 绝对路径，保持当前工作目录。

```bash
python "$NICETOOL_SKILL_ROOT/scripts/tool-cli.py" variables
python "$NICETOOL_SKILL_ROOT/scripts/tool-cli.py" variables --search api
```

命令只返回 Key 和备注，不返回 Value。对应服务端接口是
`GET /api/variables?search=...`。不要编造读取 Value 或创建、编辑、删除变量的
CLI/API；工具依赖的 Key 尚未配置时，说明需要管理员在 Admin 的“变量管理”中创建。

## 类型转换

在读取后显式转换并验证，转换失败时记录 Key，不记录原始 Value：

```python
from core.logger import get_logger
from core.variable_manager import variables

logger = get_logger(__name__)


def get_positive_int(key: str, default: str) -> int:
    raw = variables.get(key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.error("变量 {} 不是有效整数", key)
        raise ValueError(f"配置 {key} 格式错误") from None
    if value <= 0:
        raise ValueError(f"配置 {key} 必须大于 0")
    return value
```

- 布尔值要定义明确词表，例如 `true/false` 或 `1/0`，不要用 `bool(raw)`。
- JSON 值使用 `json.loads` 并校验结果结构。
- 不自动猜测数字、日期、列表或字典类型。
- 转换异常可能包含原始 Value，不使用 `logger.exception`、异常字符串或
  `raise ... from exc` 记录此类失败。上层处理配置错误时也只记录 Key 和固定错误类别，
  不附加 traceback（诊断模式可能包含局部变量）。请求异常也可能包含由变量构造的 URL。

## 工具状态与错误处理

关键配置建议在执行动作时读取，让后台修改在下一次操作生效。缺失或格式错误时：

1. 日志记录变量 Key 和不含 Value 的错误类别，不附加原始异常或 traceback。
2. 界面提示可行动信息，例如“缺少 API_BASE，请联系管理员配置”。
3. 停止依赖该配置的操作，并恢复按钮和 loading 状态。

变量读取会同步访问数据库。在 `async` 事件处理函数中使用 `run.io_bound`：

```python
from nicegui import run

api_base = await run.io_bound(lambda: variables["API_BASE"])
```

不要在模块导入阶段读取变量；否则导入失败会导致整个工具无法渲染。应在 `main` 或具体操作中读取，并提供友好错误状态。

## 安全边界

平台变量是普通字符串配置，不假设其已加密、脱敏或具备 Secret Vault 能力。不要在日志、通知、表格、下载文件或异常文本中输出 Value。用户未明确要求时，不建议把密码、Token、私钥等敏感材料存入平台变量。

固定预览和正式工具都从当前平台数据库读取变量。本地独立运行仍需要可用的平台数据库配置；不得为了让本地运行通过而硬编码生产值。
