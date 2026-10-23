# Demo Business Project: Orders and Sales

This directory provides a small synthetic business context for AI assistants and
new NiceTool users. It contains no real customer, order, or company data.

## Files

- `orders.csv`: 60 fixed synthetic orders, 10 orders per month from January to
  June 2026.
- `data.py`: helpers for loading, filtering, and aggregating orders.
- `tools/order_query.py`: an order operations workspace with filters, live
  metrics, status badges, and CSV export.
- `tools/sales_dashboard.py`: a read-only dashboard with revenue metrics,
  charts, and customer rankings.
- `tools/quote_calculator.py`: a side-effect-free quote calculator.

## Data Contract

| Field | Meaning |
| --- | --- |
| `id` | Unique order ID |
| `customer` | Synthetic customer name |
| `date` | Order date, `YYYY-MM-DD` |
| `status` | `Completed`, `In progress`, or `Canceled` |
| `amount` | Example amount as an integer |

Revenue only counts completed orders. Order counts may include every status, but
the visible UI should make the scope clear. Keyword search and status filtering
are combined; an empty search returns every matching order.

The quote calculator defaults to `24 x 199 x (1 - 12%)`, plus 6% tax and a 300
service fee. It is a calculation demo only and does not create orders or quotes.

## Development Notes

New experimental tools should use new names instead of overwriting the bundled
demo tools. Reuse the data contract in `examples.demo.data`; do not add external
dependencies, real database connections, or credentials. Exports should stay
bounded to the synthetic demo data.

For the full path from a natural language request to a published tool, see the
[demo guide](../../docs/demo.md).
