"""name: Smart quote calculator
description: Enter quantity, unit price, discount, tax, and service fees to generate a live quote summary without writing data
tags: demo,calculator,form,quote
"""

from decimal import Decimal, InvalidOperation

from nicegui import ui


def main():
    ui.label("Smart quote calculator").classes("text-2xl font-semibold")
    ui.label(
        "Enter quantity, unit price, discount, tax, and service fees to generate a live quote summary"
    ).classes("text-gray-500")

    fields = {}
    result = None

    def calculate():
        if result is None:
            return
        result.clear()
        try:
            qty, unit, rate, tax_rate, service_fee = (
                Decimal(str(fields[name].value))
                for name in ("quantity", "price", "discount", "tax", "service")
            )
            if (
                not all(
                    value.is_finite()
                    for value in (qty, unit, rate, tax_rate, service_fee)
                )
                or qty < 1
                or qty != qty.to_integral_value()
                or unit < 0
                or service_fee < 0
                or not 0 <= rate <= 100
                or not 0 <= tax_rate <= 30
            ):
                raise ValueError

            subtotal = qty * unit
            discount_amount = subtotal * rate / 100
            after_discount = subtotal - discount_amount
            tax_amount = after_discount * tax_rate / 100
            total = after_discount + tax_amount + service_fee

            with result:
                with ui.card().classes("w-full p-5 bg-primary text-white shadow-sm"):
                    ui.label("Quote total").classes("text-sm text-white")
                    ui.label(f"${total:,.2f}").classes("text-4xl font-semibold")
                    ui.label(
                        f"Unit average ${total / qty:,.2f} · Quantity {int(qty)}"
                    ).classes("text-white")
                with ui.grid(columns=2).classes("w-full gap-3"):
                    for label, value in (
                        ("Subtotal", subtotal),
                        ("Discount", -discount_amount),
                        ("Tax", tax_amount),
                        ("Service fee", service_fee),
                    ):
                        with ui.card().classes("p-4"):
                            ui.label(label).classes("text-xs text-gray-500")
                            ui.label(f"${value:,.2f}").classes("text-xl font-semibold")
        except (InvalidOperation, ValueError, TypeError):
            with result:
                ui.label(
                    "Enter an integer quantity, non-negative amounts, a 0-100 discount, and a 0-30 tax rate."
                ).classes("text-red-600")

    with ui.grid(columns=2).classes("w-full gap-4 items-start"):
        with ui.card().classes("w-full p-4 gap-3"):
            ui.label("Quote inputs").classes("text-base font-semibold")
            ui.label("Adjust any value and calculate again.").classes(
                "text-sm text-gray-500"
            )
            with ui.grid(columns=2).classes("w-full gap-3"):
                fields["quantity"] = ui.number("Quantity", value=24, min=1, step=1)
                fields["price"] = ui.number("Unit price ($)", value=199, min=0)
                fields["discount"] = ui.number("Discount (%)", value=12, min=0, max=100)
                fields["tax"] = ui.number("Tax rate (%)", value=6, min=0, max=30)
                fields["service"] = ui.number("Service fee ($)", value=300, min=0)
                for field in fields.values():
                    field.props("outlined dense").classes("w-full")
            ui.button("Calculate quote", icon="calculate", on_click=calculate).props(
                "color=primary"
            ).classes("w-full")
        result = ui.column().classes("w-full gap-3 min-w-0")
    calculate()


if __name__ == "__main__":
    main()
    ui.run()
