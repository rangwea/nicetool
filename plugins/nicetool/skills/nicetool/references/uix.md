# core.uix 组件（工具侧）

平台在 `core/uix/` 提供可复用 UI 封装，数据来自管理后台 **枚举管理**（MySQL `enum_definitions`）。只有已经由平台枚举管理维护、能提供准确 `enum_type` 的业务字段才使用 `enums_select`；工具自身的固定选项使用普通 `ui.select`，不要为了使用组件而虚构枚举。

---

## 前置条件

1. 在 `/admin` → **枚举管理** 中已创建枚举，**名称**与代码里 `enum_type` 一致（如 `ContentType`）
2. 每项结构：`key` / `value` / `remark`（Java 双参解析后一般为 `key=1`, `value=垂类组`, `remark=垂类`）
3. 工具与主应用同进程，可直接 `import core.*`

任一条件不成立时不要调用 `enums_select`。先确认该选项是否确实由平台统一维护；普通页面状态、工具模式或临时筛选项不属于托管枚举。

---

## enums_select（枚举下拉）

**导入：**

```python
from core.uix.enums_select import enums_select

# 或
from core.uix import enums_select
```

### 参数

| 参数 | 说明 |
|------|------|
| `enum_type` | 枚举管理中的名称（必填） |
| `key` | 选项**提交值**对应字段，默认 `"key"` |
| `label` | 选项**展示文案**对应字段，默认 `"value"` |
| `multiple` | `False` 单选，`True` 多选 |
| `value` | 初始值：单选 `str`，多选 `list[str]` |
| `field_label` | 表单项标题（传给 `ui.select` 的 `label`） |
| `on_change` | 变更回调 |
| `with_input` | 可输入筛选，默认 `True` |
| `use_chips` | 多选 chips，默认多选时为 `True` |
| `**select_kwargs` | 其余传给 `ui.select`（如 `classes`） |

返回 NiceGUI `Select`；`.value` 为选中项的 **key 字段值**（多选为 `list`）。组件已带 `outlined dense color=primary`，筛选区可再加 `.classes("flex-1")`。

### 单选（筛选 / 表单）

```python
from core.uix.enums_select import enums_select

content_type = enums_select(
    "ContentType",
    key="key",
    label="value",
    multiple=False,
    field_label="内容组别",
).classes("flex-1")


def search():
    code = content_type.value  # 例如 "1"
    # 查询 Mongo/MySQL 时用 code 作为条件
```

### 多选

```python
types = enums_select(
    "ContentType",
    key="key",
    label="value",
    multiple=True,
    field_label="内容组别",
    value=[],
).classes("w-full")


def search():
    codes = types.value or []  # 例如 ["1", "2"]
```

### 与 @ui.refreshable 筛选区配合

```python
@ui.refreshable
def render_filters():
    with ui.row().classes("w-full gap-3 items-center flex-wrap"):
        ct = enums_select(
            "ContentType",
            field_label="内容组别",
            on_change=lambda: render_table.refresh(),
        ).classes("flex-1")
```

### 反模式

- ❌ 在工具里写死 `{"1": "垂类组", "2": "内地组"}`
- ❌ 用 `ui.select(enum_select_options(...))` 代替 `enums_select`（能用组件就用组件）
- ❌ `enum_type` 名称与后台不一致（区分大小写）
- ❌ 为工具自身的少量固定选项虚构一个不存在的 `enum_type`

---

## core.enum_config（读写枚举数据）

下拉以外的场景（回显、字典映射、非 Select 展示）用 `core.enum_config`：

```python
from core.enum_config import (
    get_enum_values,
    enum_label,
    enum_remark,
    enum_as_dict,
    clear_enum_cache,
)

# 全量列表 [{key, value, remark}, ...]
items = get_enum_values("ContentType")

# key → 展示名
name = enum_label("ContentType", "1")  # "垂类组"

# key → 备注
note = enum_remark("ContentType", "1")  # "垂类"

# key → value 字典
mapping = enum_as_dict("ContentType")

# 后台改枚举后清缓存（长会话调试）
clear_enum_cache("ContentType")
```

| 函数 | 用途 |
|------|------|
| `get_enum_values(name)` | 原始项列表 |
| `enum_label(name, key)` | key → value 展示 |
| `enum_remark(name, key)` | key → remark |
| `enum_key_by_value(name, value)` | value → key |
| `enum_as_dict(name, field="value")` | `{key: field}` |
| `clear_enum_cache(name=None)` | 清除内存缓存 |

---

## 选型速查

| 需求 | 用法 |
|------|------|
| 平台已托管的筛选/表单枚举 | `enums_select(...)` |
| 工具自身固定选项 | `ui.select(...)` |
| 表格单元格按 key 显示文案 | `enum_label(enum_type, key)` |
| 导出/接口需要 code→name 映射 | `enum_as_dict(enum_type)` |
| 自定义组件（非 Select） | `get_enum_values` 自行渲染 |

---

## 实现位置（维护参考）

| 路径 | 说明 |
|------|------|
| `core/uix/enums_select.py` | `enums_select` 组件 |
| `core/enum_config.py` | 枚举读取 API |
| `service/enum_service.py` | 数据库 CRUD |
| `service/enum_parser.py` | Java/JSON 导入解析 |
