from unittest import TestCase
from unittest.mock import Mock

from scripts.seed_demo import seed_tools, validate_demo_target


class DemoSeedTests(TestCase):
    def test_refuses_non_demo_database(self):
        for enabled, database in ((False, "nicetool_demo"), (True, "nicetool")):
            with self.assertRaises(ValueError):
                validate_demo_target(enabled, database)

    def test_repeated_seed_updates_changed_tools(self):
        storage = Mock()
        storage.load_current.side_effect = ["user changed this", None]
        storage.save_current.return_value = {"success": True}
        result = seed_tools(storage, {"orders": "old", "sales": "new"})
        self.assertEqual(result, {"created": 1, "updated": 1, "skipped": 0})
        self.assertEqual(storage.save_current.call_count, 2)
        storage.save_current.assert_any_call(
            "demo", "orders", "old", created_by="demo-seed"
        )
        storage.save_current.assert_any_call(
            "demo", "sales", "new", created_by="demo-seed"
        )

    def test_repeated_seed_skips_unchanged_tools(self):
        storage = Mock()
        storage.load_current.return_value = "same"
        result = seed_tools(storage, {"orders": "same"})
        self.assertEqual(result, {"created": 0, "updated": 0, "skipped": 1})
        storage.save_current.assert_not_called()

    def test_failure_stops_startup(self):
        storage = Mock()
        storage.load_current.return_value = None
        storage.save_current.return_value = {
            "success": False,
            "error": "database failed",
        }
        with self.assertRaises(RuntimeError):
            seed_tools(storage, {"orders": "source"})
