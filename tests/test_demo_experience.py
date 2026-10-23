import argparse
import io
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from examples.demo.data import (
    conversion_rate,
    customer_sales,
    filter_orders,
    load_orders,
    monthly_sales,
    status_summary,
)
from scripts.doctor import check_url, diagnose
from service.tool_runtime import load_tool_entrypoint


class DemoExperienceTests(TestCase):
    def test_data_and_dashboard_agree(self):
        orders = load_orders()
        self.assertEqual(len(orders), 60)
        self.assertEqual(len({row["id"] for row in orders}), 60)
        self.assertEqual(len(filter_orders(orders, "DEMO-001")), 1)
        self.assertEqual(len(filter_orders(orders, status="Completed")), 20)
        self.assertEqual(
            sum(monthly_sales(orders).values()),
            sum(row["amount"] for row in orders if row["status"] == "Completed"),
        )
        self.assertEqual(
            status_summary(orders), {"Completed": 20, "In progress": 20, "Canceled": 20}
        )
        self.assertEqual(conversion_rate(orders), 1 / 3)
        self.assertEqual(customer_sales(orders)[0]["customer"], "Customer 4")
        self.assertEqual(filter_orders(orders, "nonexistent"), [])

    def test_all_three_tools_build_ui(self):
        paths = sorted(
            (Path(__file__).resolve().parents[1] / "examples/demo/tools").glob("*.py")
        )
        self.assertEqual(len(paths), 3)
        for path in paths:
            with self.subTest(tool=path.name):
                entrypoint, is_async = load_tool_entrypoint(
                    "demo_test_" + path.stem, str(path)
                )
                self.assertFalse(is_async)
                entrypoint()

    def test_diagnostics_accept_actual_health_response(self):
        response = io.BytesIO(b"OK")
        response.status = 200
        with patch("scripts.doctor.urllib.request.urlopen", return_value=response):
            report = diagnose("http://localhost:8000")
        self.assertTrue(report["checks"][-1]["ok"])

    def test_diagnostics_reject_credentials(self):
        for url in ("http://user:secret@localhost", "http://localhost/?token=secret"):
            with self.assertRaises(argparse.ArgumentTypeError):
                check_url(url)
