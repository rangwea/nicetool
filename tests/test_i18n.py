"""Language selection must not alter data, leak between requests, or bypass escaping."""

import json
import unittest
from pathlib import Path
from string import Formatter
from types import SimpleNamespace
from unittest.mock import patch

from core.i18n import (
    get_locale,
    html_t,
    option_labels,
    t,
)
from core.settings import settings
from public.api.auth_api import _device_authorization_html, _login_html, _password_html


class InternationalizationTests(unittest.TestCase):
    def setUp(self):
        self.locale = patch.object(settings, "language", "en-US")
        self.locale.start()

    def tearDown(self):
        self.locale.stop()

    def test_admin_summary_and_environment_display_labels(self):
        from nicegui import Client, ui

        from component.language import localized_page
        from public.admin.nicetool_environment import NiceToolEnvironmentController
        from public.admin.tool_management import ToolManagementController

        environments = NiceToolEnvironmentController()
        environments.rows = [
            {
                "id": 1,
                "name": "demo",
                "production": False,
                "enabled": True,
                "production_label": "非正式",
                "enabled_label": "启用",
            },
            {
                "id": 2,
                "name": "live",
                "production": True,
                "enabled": False,
                "production_label": "正式",
                "enabled_label": "停用",
            },
        ]
        for locale, expected in (
            (
                "en-US",
                ("Published", "Non-production", "Enabled", "Production", "Disabled"),
            ),
            ("zh-CN", ("已发布", "非正式", "启用", "正式", "停用")),
        ):
            settings.language = locale
            client = Client(localized_page("/_admin_labels_test"))
            try:
                with client:
                    ToolManagementController().render_summary()
                    environments._render_table()
                    texts = [
                        getattr(element, "_text", None)
                        for element in client.elements.values()
                    ]
                    self.assertIn(expected[0], texts)
                    table = next(
                        element
                        for element in client.elements.values()
                        if isinstance(element, ui.table)
                    )
                    self.assertEqual(
                        [
                            (row["production_label"], row["enabled_label"])
                            for row in table.rows
                        ],
                        [(expected[1], expected[2]), (expected[3], expected[4])],
                    )
                    self.assertFalse(table.rows[0]["production"])
                    self.assertTrue(table.rows[0]["enabled"])
            finally:
                client.delete()

    def test_fallback_and_placeholders(self):
        self.assertEqual(t("工具中心"), "Tool center")
        self.assertEqual(t("业务自定义名称"), "业务自定义名称")
        self.assertIn("alice", t("项目授权：{arg0}", arg0="alice"))
        settings.language = "zh-CN"
        self.assertEqual(t("工具中心"), "工具中心")

    def test_catalog_preserves_format_fields(self):
        catalog = json.loads(
            (Path(__file__).parents[1] / "core/i18n/en-US.json").read_text()
        )
        formatter = Formatter()
        for source, translated in catalog.items():
            source_fields = [
                (name, spec, conversion)
                for _, name, spec, conversion in formatter.parse(source)
                if name is not None
            ]
            translated_fields = [
                (name, spec, conversion)
                for _, name, spec, conversion in formatter.parse(translated)
                if name is not None
            ]
            self.assertEqual(sorted(source_fields), sorted(translated_fields), source)

    def test_options_preserve_machine_values(self):
        self.assertEqual(
            option_labels({"user": "普通用户", "admin": "管理员"}).keys(),
            {"user": "", "admin": ""}.keys(),
        )
        self.assertEqual(list(option_labels(["全部", "固定"])), ["全部", "固定"])
        self.assertEqual(t("面板"), "Cards")
        self.assertEqual(t("表格"), "Table")

    def test_static_vue_display_does_not_change_conditions_or_rows(self):
        markup = """<q-btn v-if="props.row.state === '固定'" :label="props.row.active ? '启用' : '禁用'" @click="$parent.$emit('edit', props.row)"><q-tooltip>编辑</q-tooltip></q-btn><span>{{ props.row.description || '暂无描述' }}</span>"""
        result = html_t(markup)
        self.assertIn("Enabled", result)
        self.assertIn("No description", result)
        self.assertIn("props.row.description", result)
        self.assertIn("固定", result)
        self.assertIn("props.row)", result)
        self.assertNotIn("暂无描述", result)

    def test_login_translates_static_text_and_escapes_values(self):
        with (
            patch(
                "public.api.auth_api.auth_service.has_local_password_users",
                return_value=True,
            ),
            patch(
                "public.api.auth_api.auth_service.external_login_enabled",
                return_value=False,
            ),
        ):
            result = _login_html(
                '/user?name="<script>', error="<script>alert(1)</script>"
            )
        self.assertIn('lang="en-US"', result)
        self.assertIn("Sign in to NiceTool", result)
        self.assertIn("Username or email", result)
        self.assertNotIn("/language/", result)
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)
        self.assertIn("Set a new password", _password_html("/"))
        self.assertIn(
            "Authorization successful",
            _device_authorization_html("code", approved=True),
        )

    def test_root_redirect_uses_env_language_despite_browser_preferences(self):
        from nicegui import Client
        from starlette.requests import Request

        from component.language import localized_page
        from public.index import index

        for locale in ("en-US", "zh-CN"):
            settings.language = locale
            opposite = "zh-CN" if locale == "en-US" else "en-US"
            request = Request(
                {
                    "type": "http",
                    "method": "GET",
                    "path": "/",
                    "query_string": b"language=fr-FR",
                    "headers": [
                        (b"host", b"localhost"),
                        (b"cookie", f"nicetool_language={opposite}".encode()),
                        (b"accept-language", opposite.encode()),
                    ],
                    "scheme": "http",
                    "server": ("localhost", 8000),
                }
            )
            client = Client(localized_page("/_i18n_test"), request=request)
            try:
                with client, patch("public.index.ui.navigate.to") as navigate:
                    index()
                    self.assertEqual(get_locale(), locale)
                    self.assertEqual(client.page.resolve_language(), locale)
                    navigate.assert_called_once_with(settings.path_for("/user"))
            finally:
                client.delete()

    def test_user_menu_only_shows_admin_link_for_admin_user(self):
        from nicegui import Client

        from component.auth_user import render_current_user
        from component.language import localized_page

        for role, should_show in (("admin", True), ("user", False)):
            user = SimpleNamespace(
                id=1,
                username="alice",
                display_name="Alice",
                email="alice@example.com",
                avatar_url="",
                password_hash="hash",
                role=role,
            )
            client = Client(localized_page(f"/_user_menu_{role}"))
            try:
                with (
                    client,
                    patch(
                        "component.auth_user.get_current_auth_user", return_value=user
                    ),
                ):
                    render_current_user()
                    texts = [
                        getattr(element, "_text", None)
                        for element in client.elements.values()
                    ]
                    self.assertEqual("Administration" in texts, should_show)
            finally:
                client.delete()
