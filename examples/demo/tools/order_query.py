"""name: Order operations workspace
description: Explore an AI-created tool with filters, live metrics, status badges, and CSV export; all data is synthetic
tags: demo,query,export,operations
"""

import csv
import io

from nicegui import ui

from examples.demo.data import filter_orders, load_orders, status_summary

STATUS_COLOR = {
    "Completed": "positive",
    "In progress": "warning",
    "Canceled": "grey",
}


def main():
    rows = load_orders()
    ui.label("Order operations workspace").classes("text-2xl font-semibold")
    ui.label(
        "60 synthetic orders with keyword search, status filters, live metrics, and CSV export"
    ).classes("text-gray-500")

    with ui.row().classes("w-full gap-3 my-2"):
        for label, value in (
            ("Total orders", len(rows)),
            (
                "Completed revenue",
                sum(row["amount"] for row in rows if row["status"] == "Completed"),
            ),
            ("Largest order", max(row["amount"] for row in rows)),
        ):
            with ui.card().classes("min-w-40 flex-1 p-4"):
                ui.label(label).classes("text-xs text-gray-500")
                ui.label(f"{value:,}").classes("text-2xl font-semibold text-gray-900")

    with ui.card().classes("w-full p-4"), ui.row().classes("w-full items-center gap-3"):
        keyword = (
            ui.input("Order ID / customer")
            .props("outlined dense clearable")
            .classes("min-w-64")
        )
        status = ui.select(
            ["All", "Completed", "In progress", "Canceled"],
            value="All",
            label="Status",
        ).props("outlined dense")
        ui.button("Search", icon="search", on_click=lambda: results.refresh()).props(
            "color=primary"
        )
        ui.button("Export results", icon="download", on_click=lambda: export()).props(
            "outline color=primary"
        )

    def selected():
        return filter_orders(rows, keyword.value or "", status.value)

    def export():
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["id", "customer", "date", "status", "amount"],
        )
        writer.writeheader()
        writer.writerows(selected())
        ui.download(output.getvalue().encode("utf-8-sig"), "demo-orders.csv")

    @ui.refreshable
    def results():
        filtered = selected()
        summary = status_summary(filtered)
        with ui.row().classes("w-full gap-2 my-2"):
            ui.badge(f"{len(filtered)} orders", color="blue")
            for key, count in summary.items():
                ui.badge(f"{key} {count}", color=STATUS_COLOR.get(key, "grey"))
        table = ui.table(
            columns=[
                {"name": key, "label": label, "field": key, "align": "left"}
                for key, label in [
                    ("id", "Order ID"),
                    ("customer", "Customer"),
                    ("date", "Date"),
                    ("status", "Status"),
                    ("amount", "Amount"),
                ]
            ],
            rows=filtered,
            row_key="id",
            pagination=10,
        ).classes("w-full")
        table.add_slot(
            "body-cell-status",
            """
            <q-td :props="props">
              <q-badge :color="props.row.status === 'Completed' ? 'positive' : (props.row.status === 'In progress' ? 'warning' : 'grey')">
                {{ props.row.status }}
              </q-badge>
            </q-td>
            """,
        )
        table.add_slot(
            "body-cell-amount",
            """
            <q-td :props="props">
              <span class="font-semibold">${{ Number(props.row.amount).toLocaleString('en-US') }}</span>
            </q-td>
            """,
        )

    results()


if __name__ == "__main__":
    main()
    ui.run()
