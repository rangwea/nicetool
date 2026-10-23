"""
project: nicetool
name: query_tool_template
description: 异步查询工具模板 - 筛选、稳定分页、完整状态和详情
creator: auto-generator
created_at: 2026-04-29
updated_at: 2026-08-20
tags: 查询, 分页, 详情
"""

import logging
from datetime import UTC, datetime
from typing import Any, NamedTuple

from nicegui import run, ui

logger = logging.getLogger(__name__)


class QueryResult(NamedTuple):
    """一页查询结果。"""

    rows: list[dict[str, Any]]
    total: int


def query_business_data(
    keyword: str,
    status: str | None,
    page: int,
    page_size: int,
) -> QueryResult:
    """查询一页业务数据；生成真实工具时替换此函数体。

    BUSINESS REPLACEMENT POINT:
    1. 使用参数化查询分别获取 total 和当前页 rows。
    2. 在服务/数据层执行权限、租户和排序字段校验。
    3. 保持结果有稳定唯一的 row key。
    """
    all_rows = [
        {
            "id": index,
            "name": f"数据项 {index}",
            "status": "正常" if index % 2 == 0 else "异常",
            "created_at": datetime.now(UTC).astimezone().strftime("%Y-%m-%d %H:%M"),
        }
        for index in range(1, 48)
    ]
    filtered = [
        row
        for row in all_rows
        if (not keyword or keyword.lower() in str(row["name"]).lower())
        and (not status or row["status"] == status)
    ]
    start = (page - 1) * page_size
    return QueryResult(filtered[start : start + page_size], len(filtered))


class DataQueryTool:
    """每个页面实例独立持有筛选、结果和分页状态。"""

    def __init__(self) -> None:
        self.current_page = 1
        self.page_size = 10
        self.total_count = 0
        self.busy = False
        self.submitted_filters: tuple[str, str | None] = ("", None)
        self.rows: list[dict[str, Any]] = []

    @property
    def total_pages(self) -> int:
        return max(1, (self.total_count + self.page_size - 1) // self.page_size)

    async def search(self, *, reset_page: bool) -> None:
        """异步加载一页数据，并保证控件在所有路径恢复。"""
        if self.busy:
            return
        if reset_page:
            self.submitted_filters = (
                (self.keyword_input.value or "").strip(),
                self.status_select.value,
            )
            self.current_page = 1
        keyword, status = self.submitted_filters

        self.busy = True
        self._set_busy(True)
        self._show_state("loading")
        try:
            result = await run.io_bound(
                query_business_data,
                keyword,
                status,
                self.current_page,
                self.page_size,
            )
            self.total_count = max(0, result.total)
            self.current_page = min(self.current_page, self.total_pages)

            # 若结果缩小导致页码越界，按修正后的页码重新查询一次。
            if self.total_count and not result.rows:
                result = await run.io_bound(
                    query_business_data,
                    keyword,
                    status,
                    self.current_page,
                    self.page_size,
                )
                self.total_count = max(0, result.total)
                self.current_page = min(self.current_page, self.total_pages)

            self.rows = result.rows
            self.table.rows = self.rows
            self.table.update()
            self._update_pagination()
            self._show_state("success" if self.rows else "empty")
        except Exception:
            logger.exception("查询业务数据失败")
            self._show_state("error", "查询失败，请稍后重试")
        finally:
            self.busy = False
            self._set_busy(False)

    async def submit_search(self) -> None:
        await self.search(reset_page=True)

    async def change_page(self, delta: int) -> None:
        target = self.current_page + delta
        if self.busy or not 1 <= target <= self.total_pages:
            return
        self.current_page = target
        await self.search(reset_page=False)

    def reset_filters(self) -> None:
        if self.busy:
            return
        self.keyword_input.set_value("")
        self.status_select.set_value(None)
        ui.notify("筛选条件已重置，点击查询后生效", type="info")

    def show_detail(self, row: dict[str, Any]) -> None:
        """以文本方式展示行数据，避免把不可信内容插入 HTML。"""
        self.detail_content.clear()
        with self.detail_content:
            for key, value in row.items():
                with ui.row().classes("w-full gap-3"):
                    ui.label(str(key)).classes("w-24 shrink-0 text-sm text-gray-500")
                    ui.label(str(value)).classes("min-w-0 flex-1 text-sm text-gray-700")
        self.detail_dialog.open()

    def _set_busy(self, busy: bool) -> None:
        if busy:
            self.search_button.disable()
            self.reset_button.disable()
            self.previous_button.disable()
            self.next_button.disable()
            return
        self.search_button.enable()
        self.reset_button.enable()
        self._update_pagination()

    def _show_state(self, state: str, message: str = "") -> None:
        self.loading_row.visible = state == "loading"
        self.empty_label.visible = state == "empty"
        self.error_label.visible = state == "error"
        self.table.visible = state == "success"
        self.pagination_row.visible = state in {"success", "empty"}
        if message:
            self.error_label.set_text(message)

    def _update_pagination(self) -> None:
        if self.total_count == 0:
            self.pagination_label.set_text("0 条")
        else:
            start = (self.current_page - 1) * self.page_size + 1
            end = min(self.current_page * self.page_size, self.total_count)
            self.pagination_label.set_text(
                f"第 {start}–{end} 条，共 {self.total_count} 条 "
                f"（{self.current_page}/{self.total_pages} 页）"
            )
        self.previous_button.set_enabled(not self.busy and self.current_page > 1)
        self.next_button.set_enabled(
            not self.busy
            and self.total_count > 0
            and self.current_page < self.total_pages
        )

    def create_ui(self) -> None:
        with ui.column().classes("w-full gap-3"):
            with ui.card().classes("w-full").props("flat"):  # noqa: SIM117
                with ui.card_section().classes("w-full py-2 px-3"):
                    with ui.row().classes("w-full gap-2 items-end flex-wrap"):
                        self.keyword_input = (
                            ui.input("关键词")
                            .props("outlined dense color=primary clearable")
                            .classes("min-w-[12rem] flex-1")
                            .mark("keyword-input")
                        )
                        # 普通工具内选项使用 ui.select；平台托管枚举才用 enums_select。
                        self.status_select = (
                            ui.select(["正常", "异常"], label="状态")
                            .props("outlined dense color=primary clearable")
                            .classes("min-w-[10rem]")
                        )
                        with ui.row().classes("gap-2 ml-auto shrink-0"):
                            self.reset_button = ui.button(
                                "重置", on_click=self.reset_filters
                            ).props("outline dense color=grey-7")
                            self.search_button = (
                                ui.button("查询", on_click=self.submit_search)
                                .props("dense color=primary")
                                .mark("search-button")
                            )

            with ui.card().classes("w-full").props("flat"):
                with ui.row().classes(
                    "w-full justify-center items-center gap-2 px-3 py-8"
                ) as self.loading_row:
                    ui.spinner("dots", size="sm", color="primary")
                    ui.label("正在查询，请稍候").classes("text-sm text-gray-600")

                self.empty_label = ui.label("没有符合当前条件的数据").classes(
                    "w-full px-3 py-8 text-center text-sm text-gray-500"
                )
                self.error_label = ui.label("").classes(
                    "w-full px-3 py-8 text-center text-sm text-negative"
                )
                self.table = (
                    ui.table(
                        columns=[
                            {
                                "name": "id",
                                "label": "ID",
                                "field": "id",
                                "align": "left",
                            },
                            {
                                "name": "name",
                                "label": "名称",
                                "field": "name",
                                "align": "left",
                            },
                            {
                                "name": "status",
                                "label": "状态",
                                "field": "status",
                                "align": "center",
                            },
                            {
                                "name": "created_at",
                                "label": "时间",
                                "field": "created_at",
                                "align": "left",
                            },
                            {
                                "name": "actions",
                                "label": "操作",
                                "field": "actions",
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
                self.table.add_slot(
                    "body-cell-actions",
                    """
                    <q-td :props="props">
                        <q-btn flat dense size="sm" color="primary" label="详情"
                            @click="$parent.$emit('detail', props.row)" />
                    </q-td>
                    """,
                )
                self.table.on("detail", lambda event: self.show_detail(event.args))

                with ui.row().classes(
                    "w-full justify-between items-center gap-2 px-3 py-2"
                ) as self.pagination_row:
                    self.pagination_label = ui.label("0 条").classes(
                        "text-sm text-gray-600"
                    )
                    with ui.row().classes("gap-2"):
                        self.previous_button = ui.button(
                            "上一页", on_click=lambda: self.change_page(-1)
                        ).props("flat dense size=sm")
                        self.next_button = ui.button(
                            "下一页", on_click=lambda: self.change_page(1)
                        ).props("flat dense size=sm")

        with ui.dialog() as self.detail_dialog:  # noqa: SIM117
            with ui.card().classes("w-full max-w-xl").props("flat"):
                ui.label("详情").classes("text-base font-semibold app-text-primary")
                self.detail_content = ui.column().classes("w-full gap-1 py-2")
                with ui.row().classes("w-full justify-end"):
                    ui.button("关闭", on_click=self.detail_dialog.close).props(
                        "flat dense"
                    )

        self._show_state("loading")
        ui.timer(0.01, self.submit_search, once=True)


def main() -> None:
    """构建每个访问者独立的查询工具。"""
    ui.page_title("数据查询工具")
    DataQueryTool().create_ui()


if __name__ in {"__main__", "__mp_main__"}:
    main()
    ui.run(title="数据查询工具", port=8080, show=True)
