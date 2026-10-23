# NiceTool 复杂视觉参考

仅在自定义组件、主题表面或复杂交互需要时加载；基础约束见 `design.md`。

## 目录

- 平台与视觉基线：页面壳、主题角色、浅色表面
- 视觉语法：字体、间距、表面、交互态、图标
- 核心组件：页头、筛选、表格、表单、摘要、规则、空状态
- 状态与反馈：文案、长任务、危险操作
- 响应式与可访问性

## 平台与视觉基线

### 平台页面壳

`component/tool_shell.render_tool_shell` 已提供：

- 浅灰页面画布；
- 固定顶栏和返回入口；
- `max-w-screen-2xl mx-auto px-4 sm:px-6 py-4` 内容容器；
- 工具名、项目名和预览标识。

工具根节点默认使用：

```python
with ui.column().classes("w-full gap-3"):
    ...
```

复杂详情、分析或多步骤页面可提升为 `gap-4`。禁止再次添加整页 `max-w-*`、`mx-auto`、`px-6` 或重复工具壳标题。

### 平台视觉语言

平台卡片已经具备 8px 圆角、无阴影和浅边框。工具页应复用而非覆盖：

- 主表面：`ui.card().classes("w-full").props("flat")`
- 次表面：卡片内部使用 `bg-gray-50 rounded-lg` 的轻量区块
- 主操作强调：`app-text-primary`、`app-bg-primary-light`、`app-border-primary`
- 辅助主题强调：`app-text-secondary`、`app-bg-secondary-light`、`app-border-secondary`
- 状态色：Quasar `positive / warning / negative / info`
- 默认正文：`text-gray-700`；辅助文字：`text-gray-500`

不要给所有卡片加 shadow，也不要用 `bordered` 反复加重平台已有边框。

### 主题角色，而非“一个颜色走到底”

NiceTool 使用一套有职责分工的主题系统。不要默认 `primary` 一定是蓝色；不同平台主题中，它可能接近深灰。先看变量在实际页面中的效果，再选择角色。

| 色彩角色 | 用途 | 推荐令牌 | 禁止用途 |
|---|---|---|---|
| Primary | 唯一主操作、任务标题、关键控制 | `--app-primary` / `--app-primary-light` | 大面积铺底、每张卡描边 |
| Secondary | 当前选择、配置关系、条件与规则 | `--app-secondary` / `--app-secondary-light` | 与 Primary 争夺主按钮 |
| Semantic | 成功、提醒、错误、处理中 | `positive / warning / negative / info` | 装饰角色卡、区分类目 |
| Neutral | 画布、正文、普通表面和分隔 | `gray-50` 至 `gray-900` | 承担唯一选中态 |

推荐近似比例：75% 中性色、18% 浅主题表面、7% 实色主题与状态。比例用于视觉收敛，不要求机械计算。

### 一套主题的组合规则

一个页面最多使用两种非语义主题角色：Primary 与 Secondary。二者必须分工，不按组件轮流上色。

```text
Primary   = “我要做什么”    主按钮、任务标题、关键输入焦点
Secondary = “我正在看什么” 选中项、关系配置、规则、条件标签
Semantic  = “结果怎么样”    已启用、成功、警告、失败
```

- 页面只有 Primary 时：用于简单查询、录入和单动作工具。
- 引入 Secondary 时：必须存在持续选择、配置关系、流程条件或左右联动。
- `positive` 只表示“已启用/已完成”，不可拿绿色装饰普通卡片。
- 选中态不能只有灰底或只有文字变色；至少同时使用底色、边线、字重中的两项。
- 若 Primary 在实际主题中接近黑灰，选中态与关系型信息优先使用 Secondary，避免整页发灰。

### 浅色主题表面的生成

优先使用平台 light 令牌。需要更细层级时，使用局部命名空间和 `color-mix`，不得写死十六进制色值：

```python
ui.add_css("""
    .contract-tool .selected-surface {
        color: var(--app-secondary);
        background: var(--app-secondary-light);
        border-color: color-mix(in srgb, var(--app-secondary) 35%, transparent);
        border-left: 3px solid var(--app-secondary);
    }
    .contract-tool .related-chip {
        color: var(--app-secondary);
        background: color-mix(in srgb, var(--app-secondary) 12%, white);
    }
""")
```

同一区域的浅底、边框和文字应来自同一主题变量，形成色相一致、明度不同的一套颜色，而不是拼接多个现成状态色。

---

## 视觉语法

### 字体层级

| 角色 | 推荐类 | 使用原则 |
|---|---|---|
| 页面任务标题 | `text-lg font-semibold app-text-primary` | 页面最多一个 |
| 对象或关键结论 | `text-base font-semibold text-gray-900` | 摘要区焦点 |
| 分区标题 | `text-sm font-semibold text-gray-800` | 有真实分组时才用 |
| 正文 | `text-sm text-gray-700` | 默认业务信息 |
| 辅助信息 | `text-xs text-gray-500` | 时间、来源、口径 |
| 核心数字 | `text-2xl font-semibold text-gray-900` | 仅指标或结果摘要 |

- 不使用 `text-3xl` 及以上标题。
- 一个局部区域最多一个最高字重；不要把标签和值全部加粗。
- 副标题最多一行，必须补充范围、状态或用途，不重复标题。
- 长标识不静默截断；允许换行、复制或 tooltip。

### 间距节奏

使用 2 / 3 / 4 三级节奏：

| 关系 | 推荐间距 |
|---|---|
| 同组紧密元素 | `gap-1` / `gap-2` |
| 同一区块元素 | `gap-3` |
| 不同语义区块 | `gap-4` 或分隔线 |

Card 内容默认 `py-3 px-3 sm:px-4`。表格容器可去掉多余内边距。组间距必须明显大于组内间距。

### 表面层级

单页通常只需要三层：

1. **画布**：平台浅灰背景，不自行绘制。
2. **主表面**：表单、表格、结果等核心 card。
3. **内嵌表面**：摘要、提示、关联信息，使用 `bg-gray-50 rounded-lg px-3 py-2`。

禁止 card 内再套同样的 card。需要分组时使用 `ui.card_section()`、浅分隔线或内嵌表面。

### 视觉锚点

每个页面至少建立一个、最多两个视觉锚点：

- 主题色主按钮；
- 左侧主题色细边的当前状态块；
- 核心结果数字；
- 主数据表的对象列。

不要同时使用大色块、彩色指标、多个实心按钮和高饱和 badge。

### 可交互表面的四态

列表项、目录项、流程类型等可选择表面必须至少定义 default、hover、selected、disabled 四态：

| 状态 | 表现 |
|---|---|
| Default | 白色或极浅中性表面，边框透明 |
| Hover | 浅 Secondary 表面，不改变布局尺寸 |
| Selected | Secondary 浅底 + 左侧 3–4px 实色边 + 强化标题 |
| Disabled | 降低透明度并保留状态文字，不只变灰 |

避免选中项仍像普通灰卡。选中态是导航信息，不是装饰，必须能在一秒内定位。

### 图标

图标用于导航、状态识别和紧凑操作，不用于“让按钮更好看”。

- 普通按钮默认纯文字。
- 表格窄操作列可使用图标按钮，必须配 tooltip。
- 空状态可使用一个低对比图标。
- 页面标题、指标卡和每个输入框前不要机械加图标。

---

## 核心组件

### 任务页头

平台已有工具名时，内页头表达当前任务或对象：

```python
with ui.row().classes("w-full justify-between items-start gap-3 flex-wrap"):
    with ui.column().classes("gap-0.5 min-w-0"):
        ui.label("待处理合同").classes("text-lg font-semibold app-text-primary")
        ui.label("128 条 · 更新于 10:32").classes("text-xs text-gray-500")
    with ui.row().classes("gap-2 shrink-0"):
        ui.button("导出", on_click=export).props("outline dense color=grey-7")
        ui.button("新增合同", on_click=create).props("dense color=primary")
```

无对象、范围或页面级动作时，省略内页头。

### 筛选表面

```python
with ui.card().classes("w-full").props("flat"):
    with ui.card_section().classes("w-full py-3 px-3 sm:px-4"):
        with ui.row().classes("w-full gap-2 items-center flex-wrap"):
            ui.input(placeholder="合同号或名称").props(
                "outlined dense clearable color=primary"
            ).classes("min-w-[14rem] flex-1")
            # enums_select(...).classes("min-w-[10rem]")
            with ui.row().classes("gap-2 ml-auto shrink-0"):
                ui.button("重置", on_click=reset).props("flat dense color=grey-7")
                ui.button("查询", on_click=search).props("dense color=primary")
```

- 1–3 个高频条件保持单行；4 个以上折叠低频项。
- 简单字段使用 placeholder，复杂或必填字段使用 label。
- 生效条件数量放在结果摘要，不堆彩色 chips。

### 数据表

```python
table = (
    ui.table(columns=columns, rows=rows, row_key="id")
    .props("flat dense separator=horizontal color=primary")
    .classes("w-full")
)
```

- 第一列优先放可识别对象，最后一列放操作。
- 名称、描述左对齐；数字右对齐；状态和短枚举可居中。
- 列超过 8 个时隐藏低频列或提供详情，不依赖横向滚动展示全部字段。
- 仅状态、风险、版本使用 badge；普通枚举和文本使用纯文字。
- 表格上方工具栏只放真实功能：结果数、排序、列显示、导出。
- 分页同时显示范围与总数，例如“第 21–40 条，共 128 条”。
- 多选后才出现批量操作条，不长期占据页面。

### 表单

- 输入统一 `outlined dense color=primary`，禁止 `filled`。
- 必填、格式和跨字段错误靠近字段显示；提交失败同时给概要通知。
- 单行短字段使用两列网格，描述、备注、JSON 等长字段独占一行。
- 对话框适合不超过 6 个字段的短任务；复杂编辑使用完整页面。
- 表单底部保持“取消/重置”在左或弱化，“保存/提交”在右且唯一实心。

### 摘要带

当 3–5 个关键值需要快速扫描时，使用一条轻量摘要带，而不是多张卡：

```python
with ui.element("div").classes(
    "w-full grid grid-cols-2 lg:grid-cols-4 gap-px bg-gray-200 rounded-lg overflow-hidden"
):
    for label, value in summary:
        with ui.column().classes("bg-white px-3 py-2 gap-0"):
            ui.label(label).classes("text-xs text-gray-500")
            ui.label(value).classes("text-sm font-semibold text-gray-900")
```

只有核心数字需要独立强调时才使用指标卡。指标最多 4 个，结构和高度保持一致。

### 配置组带

人员组、角色组、权限组等“多个同类配置共同影响下方内容”的场景，使用连续配置带，而不是若干悬浮卡片：

```python
with ui.element("div").classes(
    "role-band w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-px rounded-lg overflow-hidden"
):
    for group in groups:
        with ui.column().classes("role-tile px-3 py-3 gap-2 min-w-0"):
            ...
```

局部主题样式：

```css
.approval-tool .role-band {
    background: color-mix(in srgb, var(--app-secondary) 20%, transparent);
}
.approval-tool .role-tile {
    background: color-mix(in srgb, var(--app-secondary) 7%, white);
    border-top: 3px solid var(--app-secondary);
}
.approval-tool .member-chip {
    color: var(--app-secondary);
    background: color-mix(in srgb, var(--app-secondary) 13%, white);
}
```

- 整组只使用一个主题色，通过明度区分层级；不要给每个角色分配一种颜色。
- 成员适合轻量 chip；职责说明保持中性辅助文字。
- 编辑仍是文字按钮，不给每张配置项加图标。
- 当配置组超过 6 个时，优先换行、分页或折叠，不无限压缩单元格。

### 条件与规则

流程条件、匹配规则、跳过逻辑属于关系信息，默认使用 Secondary 浅色标签或左边线说明块：

- 条件标签表达“何时进入”，不使用 `warning`，除非条件本身存在风险。
- 规则说明与条件标签使用同一色系，使用户建立稳定关联。
- 标签只包裹短条件；长规则换成说明块，避免整行大胶囊。
- 颜色之外保留“进入条件”“规则说明”等文字标签。

### 提示与风险

- 中性说明：浅灰内嵌表面，不使用 badge。
- 操作提示：`ui.banner()` 或左侧主题色细边块，控制在 1–3 行。
- 风险警告：`warning`；阻断错误：`negative`；不要用红色表达普通注意事项。
- 可关闭提示只用于临时信息；关键业务限制必须持续可见。

### 空状态

空状态应解释原因并给一个下一步：

```python
with ui.column().classes("w-full items-center py-10 gap-1.5"):
    ui.icon("inbox").classes("text-4xl text-gray-300")
    ui.label("暂无匹配结果").classes("text-sm font-medium text-gray-700")
    ui.label("调整筛选条件后重试").classes("text-xs text-gray-500")
    ui.button("清除筛选", on_click=reset).props("flat dense color=primary")
```

不要同时提供多个空状态按钮。

---

## 状态与反馈

### 状态必须改变界面

Toast 只做即时反馈，不能代替页面状态。

| 状态 | 页面表现 |
|---|---|
| 初始 | 说明输入要求和主动作 |
| 加载 | 禁用重复动作，显示当前步骤或骨架 |
| 空 | 解释没有结果的原因和下一步 |
| 成功 | 展示结果摘要、异常和可继续动作 |
| 失败 | 保留输入，说明原因，并提供重试或修正路径 |

### 文案规则

- 成功：“已回填 128 行，3 行需人工确认”。
- 失败：“处理失败：未找到‘合同号’列，请使用模板文件”。
- 进行中：“正在查询合同 42/128”。
- 禁止只写“成功”“失败”“处理中”。

### 长任务

- 使用 `run.io_bound` 或异步任务，避免阻塞事件循环。
- 运行期间禁用触发按钮并防止重复提交。
- 超过数秒的任务显示阶段或进度；完成后保留摘要，不立即清空。
- 可恢复错误保留用户输入；不可恢复错误说明如何修复。

### 危险操作

- 删除、覆盖、批量更新、正式发布必须确认影响范围。
- 确认按钮使用明确动词，如“删除 12 条记录”，不用“确定”。
- 危险操作不与主操作并列成同等权重；放入次级菜单或独立确认流程。

---

## 响应式与可访问性

- 所有操作行使用 `flex-wrap`；主要动作在窄屏仍可见。
- 网格从 `grid-cols-1` 起步，再使用 `sm:`、`lg:` 扩展。
- 双栏工作区在 `lg` 以下回落为单列。
- 触控目标保持可点击，不用极小文字模拟按钮。
- 状态不只依赖颜色，同时显示文字、数值或符号。
- 图标按钮必须有 tooltip；输入必须有 label、placeholder 或邻近说明。
- 正文对比度不低于 `text-gray-500`；`text-gray-300/400` 仅用于图标或极弱占位。
- 键盘操作顺序遵循视觉顺序；对话框打开后主任务清晰，关闭路径明确。
- 长文本允许换行或查看详情，不用固定窄宽度强制截断。

---
