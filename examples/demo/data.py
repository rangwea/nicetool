"""Synthetic order data for the standalone demo."""

import csv
from pathlib import Path


def load_orders() -> list[dict]:
    with (Path(__file__).parent / "orders.csv").open(
        encoding="utf-8", newline=""
    ) as source:
        return [{**row, "amount": int(row["amount"])} for row in csv.DictReader(source)]


def filter_orders(
    orders: list[dict], keyword: str = "", status: str = "All"
) -> list[dict]:
    keyword = keyword.strip().lower()
    return [
        row
        for row in orders
        if (
            not keyword
            or keyword in row["id"].lower()
            or keyword in row["customer"].lower()
        )
        and (status == "All" or row["status"] == status)
    ]


def monthly_sales(orders: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for row in orders:
        month = row["date"][:7]
        totals.setdefault(month, 0)
        if row["status"] == "Completed":
            totals[month] += row["amount"]
    return dict(sorted(totals.items()))


def status_summary(orders: list[dict]) -> dict[str, int]:
    result = {"Completed": 0, "In progress": 0, "Canceled": 0}
    for row in orders:
        result[row["status"]] = result.get(row["status"], 0) + 1
    return result


def customer_sales(orders: list[dict]) -> list[dict]:
    totals: dict[str, int] = {}
    counts: dict[str, int] = {}
    for row in orders:
        customer = row["customer"]
        counts[customer] = counts.get(customer, 0) + 1
        totals.setdefault(customer, 0)
        if row["status"] == "Completed":
            totals[customer] += row["amount"]
    return [
        {"customer": customer, "orders": counts[customer], "sales": totals[customer]}
        for customer in sorted(counts, key=lambda item: totals[item], reverse=True)
    ]


def conversion_rate(orders: list[dict]) -> float:
    if not orders:
        return 0
    completed = len([row for row in orders if row["status"] == "Completed"])
    return completed / len(orders)
