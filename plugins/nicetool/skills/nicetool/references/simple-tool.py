"""
project: nicetool
name: simple_tool_template
description: 异步简单工具模板 - 紧凑表单、完整状态和结果表格
creator: auto-generator
created_at: 2026-04-29
updated_at: 2026-08-20
tags: 表单, 异步任务, 结果展示
"""

import logging
from typing import Any

from nicegui import run, ui

logger = logging.getLogger(__name__)


def execute_business_operation(name: str, category: str | None) -> dict[str, Any]:
    """执行阻塞业务操作；生成真实工具时替换此函数体。

    BUSINESS REPLACEMENT POINT:
    在这里调用同步数据库、HTTP 或文件 API。不要在此函数更新 UI。
    """
    return {
        "id": 1,
        "name": name,
        "category": category or "未分类",
        "status": "已完成",
    }


def main() -> None:
    """构建每个访问者独立的工具实例。"""
    ui.page_title("简单工具示例")
    rows: list[dict[str, Any]] = []
    busy = False

    def show_state(state: str, message: str = "") -> None:
        loading_row.visible = state == "loading"
        initial_label.visible = state == "initial"
        result_table.visible = state == "success"
        empty_label.visible = state == "empty"
        error_label.visible = state == "error"
        if message:
            error_label.set_text(message)

    def reset_form() -> None:
        if busy:
            return
        name_input.set_value("")
        category_select.set_value(None)
        rows.clear()
        result_table.rows = []
        result_table.update()
        show_state("initial")
        ui.notify("已重置", type="info")

    async def submit() -> None:
        nonlocal busy
        name = (name_input.value or "").strip()
        if not name:
            ui.notify("请输入名称", type="warning")
            return
        if busy:
            return

        busy = True
        submit_button.disable()
        reset_button.disable()
        show_state("loading")
        try:
            result = await run.io_bound(
                execute_business_operation,
                name,
                category_select.value,
            )
            rows[:] = [result] if result else []
            result_table.rows = rows
            result_table.update()
            show_state("success" if rows else "empty")
            ui.notify("处理完成", type="positive")
        except Exception:
            logger.exception("简单工具业务操作失败")
            show_state("error", "处理失败，请稍后重试")
        finally:
            busy = False
            submit_button.enable()
            reset_button.enable()

    with ui.column().classes("w-full gap-3"):
        with ui.card().classes("w-full").props("flat"):  # noqa: SIM117
            with ui.card_section().classes("w-full py-2 px-3"):
                with ui.row().classes("w-full gap-2 items-end flex-wrap"):
                    name_input = (
                        ui.input(
                            "名称",
                            validation={
                                "请输入名称": lambda value: bool((value or "").strip())
                            },
                        )
                        .props("outlined dense color=primary clearable")
                        .classes("min-w-[12rem] flex-1")
                        .mark("name-input")
                    )
                    # 普通工具内选项使用 ui.select；平台托管枚举才用 enums_select。
                    category_select = (
                        ui.select(["选项A", "选项B", "选项C"], label="类型")
                        .props("outlined dense color=primary clearable")
                        .classes("min-w-[10rem] flex-1")
                    )
                    with ui.row().classes("gap-2 ml-auto shrink-0"):
                        reset_button = ui.button("重置", on_click=reset_form).props(
                            "outline dense color=grey-7"
                        )
                        submit_button = (
                            ui.button("提交", on_click=submit)
                            .props("dense color=primary")
                            .mark("submit-button")
                        )

        with ui.card().classes("w-full").props("flat"):
            initial_label = ui.label("填写信息并提交后显示处理结果").classes(
                "w-full px-3 py-6 text-center text-sm text-gray-500"
            )
            with ui.row().classes(
                "w-full justify-center items-center gap-2 px-3 py-6"
            ) as loading_row:
                ui.spinner("dots", size="sm", color="primary")
                ui.label("正在处理，请稍候").classes("text-sm text-gray-600")
            empty_label = ui.label("处理完成，但没有可展示的结果").classes(
                "w-full px-3 py-6 text-center text-sm text-gray-500"
            )
            error_label = ui.label("").classes(
                "w-full px-3 py-6 text-center text-sm text-negative"
            )
            result_table = (
                ui.table(
                    columns=[
                        {"name": "id", "label": "ID", "field": "id", "align": "left"},
                        {
                            "name": "name",
                            "label": "名称",
                            "field": "name",
                            "align": "left",
                        },
                        {
                            "name": "category",
                            "label": "类型",
                            "field": "category",
                            "align": "left",
                        },
                        {
                            "name": "status",
                            "label": "状态",
                            "field": "status",
                            "align": "center",
                        },
                    ],
                    rows=[],
                    row_key="id",
                )
                .props("flat dense color=primary")
                .classes("w-full")
                .mark("result-table")
            )
            show_state("initial")


if __name__ in {"__main__", "__mp_main__"}:
    main()
    ui.run(title="简单工具示例", port=8080, show=True)
