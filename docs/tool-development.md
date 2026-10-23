# 工具开发

[返回文档索引](README.md)

## 文件与入口

工具是单个 Python 文件，通过项目名和文件名定位，例如 `demo/hello.py`。`name` 元数据是显示标题，URL 中的工具名是文件名去掉 `.py`。

```python
"""name: Hello NiceTool
description: 演示交互输入
creator: contributor
tags: demo
"""

from nicegui import ui


def main():
    with ui.column().classes("w-full gap-4"):
        ui.label("Hello NiceTool").classes("text-xl font-semibold")
        ui.button("点击", on_click=lambda: ui.notify("操作成功"))


if __name__ == "__main__":
    main()
    ui.run()
```

支持 `def main()` 与 `async def main()`。UI 构建放进 `main()`，`ui.run()` 只能位于本地启动保护块中。模块导入时会执行顶层语句，应避免顶层网络请求和写操作；不再支持没有 `main()` 的旧式顶层 UI 脚本。

平台要求调用入口无需传参。保持入口直接、无装饰器，便于预览和正式执行采用相同逻辑。

## 数据与共享配置

业务数据库连接通过 `core.datasource_manager` 管理，平台变量通过 `core.variable_manager` 读取。使用之前先由管理员登记配置；不要在工具源码中硬编码真实连接密码或 Token。

枚举使用 `core.enum_config` 中的 `get_enum_values()`、`enum_options()` 等接口。具体接口可查看源码与 Skill 参考文件。

耗时查询避免阻塞 UI 事件循环；查询列表应有筛选和分页，导出应有数量上限。事务、参数校验和业务写入权限由工具开发者负责实现。

## 生命周期

1. 本地创建文件，或使用 CLI `create`。
2. 使用 `preview` 验证 UI、查询和异常处理。
3. 使用 `prelog` 查看预览错误。
4. 确认目标项目与实例，使用 `publish` 上传源码。
5. 使用 `status` 核对正式版本，并打开正式地址。

命令示例见[CLI 指南](nicetool-skill.md)。预览执行也会运行真实 Python 代码，不自动回滚工具对业务数据的写入。

## 平台实现

- `service/tool_metadata.py`：模块 docstring 元数据解析。
- `service/tool_runtime.py`：入口校验和模块加载。
- `service/tool_storage.py`：MySQL 源码版本与运行缓存恢复。
- `service/tool_lifecycle_service.py`：发布、回滚、删除及操作记录。

正式内容以数据库为准，不要把手工修改运行缓存当成发布。

## 工具名称与源码契约

项目名和工具名仅允许小写字母、数字、下划线和连字符；项目名最长 100 个字符，工具名最长 197 个字符。工具名不包含 `.py`。平台不会自动转小写、替换空格或剥离扩展名；非法名称会被拒绝，API 返回 HTTP 422。工具标题可使用中文，与工具标识符分开。

发布必须上传包含顶层 `main()` 的 Python 源码。`POST /api/tools/{project}/{name}/publish` 必须携带 JSON 请求体 `{"content": "..."}`；缺失请求体、缺失 content 或空字符串返回 HTTP 422。源码语法或入口错误返回 HTTP 400。CLI 默认读取本地 `tools/{project}/{name}.py` 并上传，也可使用 `--file` 或 `--stdin`。服务端不会从当前数据库版本或本地运行缓存推断待发布内容。

MySQL 保存正式源码和版本，本地 `tools/` 仅作为可恢复的运行缓存。恢复历史源码请在后台使用版本回滚，它会创建新版本。工具详情不返回 revision，CLI `get --output` 仅写入源码文件；平台未提供乐观锁冲突保护。
