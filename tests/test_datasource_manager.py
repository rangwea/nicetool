import unittest
from datetime import timedelta
from unittest.mock import MagicMock, patch

from core.datasource_manager import MongoDBWrapper
from models.datasource import DataSource


class MongoDBWrapperTest(unittest.TestCase):
    def test_mongodb_connections_use_configured_timezone(self):
        """MongoDB 连接应使用数据源配置的时区解码 BSON 时间。"""
        config = DataSource(
            name="mongo-test",
            type="mongodb",
            host="127.0.0.1",
            port=27017,
            username="tester",
            password="secret",
            database="sample",
            timezone="UTC",
        )
        client = MagicMock()

        with patch(
            "core.datasource_manager.MongoClient", return_value=client
        ) as constructor:
            MongoDBWrapper(config).connect()

        options = constructor.call_args.kwargs
        self.assertIn("tz_aware", options)
        self.assertIn("tzinfo", options)
        self.assertIs(options["tz_aware"], True)
        self.assertEqual(options["tzinfo"].utcoffset(None), timedelta(0))

    def test_mongodb_connection_keeps_driver_default_without_timezone(self):
        """MongoDB 数据源未配置时区时不应传入时区参数。"""
        config = DataSource(
            name="mongo-test",
            type="mongodb",
            host="127.0.0.1",
            port=27017,
            username="tester",
            password="secret",
            database="sample",
        )
        client = MagicMock()

        with patch(
            "core.datasource_manager.MongoClient", return_value=client
        ) as constructor:
            try:
                MongoDBWrapper(config).connect()
            except Exception as error:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                self.fail(f"未配置时区不应导致连接失败: {error}")

        options = constructor.call_args.kwargs
        self.assertNotIn("tz_aware", options)
        self.assertNotIn("tzinfo", options)
