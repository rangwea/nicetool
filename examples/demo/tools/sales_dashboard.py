"""name: Sales operations dashboard
description: Turn synthetic orders into revenue metrics, monthly trends, status distribution, and customer rankings
tags: demo,chart,analytics,dashboard
"""

from nicegui import ui

from examples.demo.data import (
    conversion_rate,
    customer_sales,
    load_orders,
    monthly_sales,
    status_summary,
)


def main():
    orders = load_orders()
    completed = [row for row in orders if row["status"] == "Completed"]
    totals = monthly_sales(orders)
    statuses = status_summary(orders)
    customers = customer_sales(orders)[:6]
    total_sales = sum(row["amount"] for row in completed)

    ui.label("Sales operations dashboard").classes("text-2xl font-semibold")
    ui.label(
        "Synthetic data from January to June 2026; revenue counts completed orders only"
    ).classes("text-gray-500")

    with ui.row().classes("w-full gap-4"):
        for label, value, hint in (
            ("Total orders", len(orders), "All statuses"),
            ("Completed revenue", f"${total_sales:,}", "Completed orders"),
            ("Conversion rate", f"{conversion_rate(orders):.0%}", "Completed / all"),
            (
                "Average order value",
                f"${(total_sales / max(len(completed), 1)):,.0f}",
                "Completed orders",
            ),
        ):
            with ui.card().classes("min-w-44 flex-1 p-4"):
                ui.label(label).classes("text-xs text-gray-500")
                ui.label(value).classes("text-2xl font-semibold text-gray-900")
                ui.label(hint).classes("text-xs text-gray-400")

    with ui.grid(columns=2).classes("w-full gap-4"):
        with ui.card().classes("p-4"):
            ui.label("Monthly revenue trend").classes("font-semibold")
            ui.echart(
                {
                    "tooltip": {"trigger": "axis"},
                    "grid": {"left": 42, "right": 20, "top": 30, "bottom": 36},
                    "xAxis": {"type": "category", "data": list(totals)},
                    "yAxis": {"type": "value", "name": "$"},
                    "series": [
                        {
                            "name": "Completed revenue",
                            "type": "bar",
                            "data": list(totals.values()),
                            "itemStyle": {"color": "#2563eb"},
                        }
                    ],
                }
            ).classes("w-full h-72")

        with ui.card().classes("p-4"):
            ui.label("Order status distribution").classes("font-semibold")
            ui.echart(
                {
                    "tooltip": {"trigger": "item"},
                    "legend": {"bottom": 0},
                    "series": [
                        {
                            "name": "Order status",
                            "type": "pie",
                            "radius": ["42%", "68%"],
                            "data": [
                                {"name": key, "value": value}
                                for key, value in statuses.items()
                            ],
                        }
                    ],
                }
            ).classes("w-full h-72")

    ui.label("Customer contribution ranking").classes("text-lg font-semibold mt-2")
    table = ui.table(
        columns=[
            {
                "name": "customer",
                "label": "Customer",
                "field": "customer",
                "align": "left",
            },
            {"name": "orders", "label": "Orders", "field": "orders", "align": "left"},
            {
                "name": "sales",
                "label": "Completed revenue",
                "field": "sales",
                "align": "left",
            },
        ],
        rows=customers,
        row_key="customer",
        pagination=6,
    ).classes("w-full")
    table.add_slot(
        "body-cell-sales",
        """
        <q-td :props="props">
          <span class="font-semibold">${{ Number(props.row.sales).toLocaleString('en-US') }}</span>
        </q-td>
        """,
    )


if __name__ == "__main__":
    main()
    ui.run()
