"""
project: website
name: order_workspace
description: A synthetic order workspace with filtering and CSV export.
creator: codex
created_at: 2026-10-26
updated_at: 2026-10-26
tags: orders, search, reporting, export
"""

import csv
import io
import os
from typing import Any

from nicegui import ui

ORDERS: tuple[dict[str, Any], ...] = (
    {"id": "NT-1001", "customer": "Acme", "status": "Completed", "amount": 1240.00},
    {"id": "NT-1002", "customer": "Birch", "status": "In progress", "amount": 860.50},
    {"id": "NT-1003", "customer": "Cedar", "status": "Completed", "amount": 2150.00},
    {"id": "NT-1004", "customer": "Acme", "status": "Canceled", "amount": 430.25},
    {"id": "NT-1005", "customer": "Birch", "status": "Completed", "amount": 975.75},
    {"id": "NT-1006", "customer": "Cedar", "status": "In progress", "amount": 1680.00},
    {"id": "NT-1007", "customer": "Acme", "status": "Completed", "amount": 720.00},
    {"id": "NT-1008", "customer": "Cedar", "status": "Canceled", "amount": 510.50},
)


def main() -> None:
    """Render the order workspace with connection-local filter state."""
    is_zh = os.getenv("LANGUAGE", "") == "zh-CN"
    text = {
        "title": "订单工作台" if is_zh else "Order workspace",
        "subtitle": "AI 创建，团队共享。" if is_zh else "AI-built. Team-ready.",
        "total": "订单数" if is_zh else "Total orders",
        "revenue": "已完成金额" if is_zh else "Completed revenue",
        "average": "平均订单金额" if is_zh else "Average amount",
        "search": "搜索订单" if is_zh else "Search orders",
        "status": "状态" if is_zh else "Status",
        "search_button": "查询" if is_zh else "Search",
        "export": "导出 CSV" if is_zh else "Export CSV",
        "matches": "笔匹配订单" if is_zh else "matching orders",
        "order_id": "订单编号" if is_zh else "Order ID",
        "customer": "客户" if is_zh else "Customer",
        "amount": "金额" if is_zh else "Amount",
        "empty": "没有匹配的订单" if is_zh else "No matching orders",
    }
    status_labels = {
        "All": "全部" if is_zh else "All",
        "Completed": "已完成" if is_zh else "Completed",
        "In progress": "处理中" if is_zh else "In progress",
        "Canceled": "已取消" if is_zh else "Canceled",
    }

    keyword_input: Any = None
    status_select: Any = None
    filtered_rows: list[dict[str, Any]] = list(ORDERS)

    def apply_filters() -> list[dict[str, Any]]:
        keyword = str(keyword_input.value or "").strip().casefold()
        selected_status = status_select.value or "All"
        return [
            dict(order)
            for order in ORDERS
            if (
                not keyword
                or keyword in order["id"].casefold()
                or keyword in order["customer"].casefold()
            )
            and (selected_status == "All" or order["status"] == selected_status)
        ]

    def search() -> None:
        nonlocal filtered_rows
        filtered_rows = apply_filters()
        results.refresh()

    def export_csv() -> None:
        rows = apply_filters()
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(["Order ID", "Customer", "Status", "Amount"])
        for row in rows:
            writer.writerow(
                [row["id"], row["customer"], row["status"], f"{row['amount']:.2f}"]
            )
        ui.download(buffer.getvalue().encode("utf-8-sig"), filename="orders.csv")

    @ui.refreshable
    def results() -> None:
        count_label = f"{len(filtered_rows)} {text['matches']}"
        ui.label(count_label).classes("text-sm font-medium text-gray-600")
        if not filtered_rows:
            ui.label(text["empty"]).classes(
                "w-full py-8 text-center text-sm text-gray-500"
            )
            return

        display_rows = [
            {
                **row,
                "status": status_labels[row["status"]],
                "amount": f"${row['amount']:,.2f}",
            }
            for row in filtered_rows
        ]
        ui.table(
            columns=[
                {
                    "name": "id",
                    "label": text["order_id"],
                    "field": "id",
                    "align": "left",
                },
                {
                    "name": "customer",
                    "label": text["customer"],
                    "field": "customer",
                    "align": "left",
                },
                {
                    "name": "status",
                    "label": text["status"],
                    "field": "status",
                    "align": "left",
                },
                {
                    "name": "amount",
                    "label": text["amount"],
                    "field": "amount",
                    "align": "right",
                },
            ],
            rows=display_rows,
            row_key="id",
        ).props("flat dense separator=horizontal").classes("w-full")

    total_revenue = sum(
        order["amount"] for order in ORDERS if order["status"] == "Completed"
    )
    average_amount = sum(order["amount"] for order in ORDERS) / len(ORDERS)

    with ui.column().classes("w-full gap-3"):
        with ui.column().classes("w-full gap-1 pb-1"):
            ui.label("SYNTHETIC DATA").classes(
                "text-xs font-semibold tracking-widest text-gray-500"
            )
            ui.label(text["title"]).classes("text-2xl font-semibold text-gray-900")
            ui.label(text["subtitle"]).classes("text-sm text-gray-500")

        with ui.row().classes("w-full gap-3 flex-wrap"):
            for label, value in (
                (text["total"], str(len(ORDERS))),
                (text["revenue"], f"${total_revenue:,.2f}"),
                (text["average"], f"${average_amount:,.2f}"),
            ):
                with (
                    ui.card()
                    .props("flat bordered")
                    .classes("min-w-[12rem] flex-1 bg-white")
                ):
                    ui.label(label).classes("text-xs font-medium text-gray-500")
                    ui.label(value).classes("text-xl font-semibold text-gray-900")

        with (
            ui.card().props("flat bordered").classes("w-full bg-white"),
            ui.row().classes("w-full items-end gap-2 flex-wrap"),
        ):
            keyword_input = (
                ui.input(label=text["search"])
                .props("outlined dense clearable color=primary")
                .classes("min-w-[14rem] flex-1")
            )
            status_select = (
                ui.select(
                    options=status_labels,
                    value="All",
                    label=text["status"],
                )
                .props("outlined dense color=primary")
                .classes("min-w-[11rem]")
            )
            ui.button(text["search_button"], on_click=search).props(
                "dense color=primary"
            )
            ui.button(text["export"], on_click=export_csv).props(
                "outline dense color=primary"
            )

        with ui.card().props("flat bordered").classes("w-full bg-white"):
            results()


if __name__ in {"__main__", "__mp_main__"}:
    main()
    ui.run(title="Order workspace", port=8080, show=True)
