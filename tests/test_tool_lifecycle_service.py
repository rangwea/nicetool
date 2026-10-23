import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from sqlalchemy import BigInteger

from core.auth.actor import Actor, system_actor
from models.tool import Tool, ToolLifecycleEvent, ToolVersion
from service import admin_tool_service
from service.tool_lifecycle_service import (
    LifecycleResult,
    _build_event,
    _check_scope,
    delete_tool,
    get_tool_state,
    lifecycle_error,
    lifecycle_success,
    list_tool_events,
    preview_tool,
    publish_tool,
    record_lifecycle_event,
    restore_runtime_cache,
    rollback_tool,
)


def server_default_sql(column):
    return str(column.server_default.arg).upper()


class _ExecResult:
    def __init__(self, *, first=None, all_rows=None):
        self._first = first
        self._all_rows = all_rows or []

    def first(self):
        return self._first

    def all(self):
        return self._all_rows


class _FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.statements = []

    def exec(self, statement):
        self.statements.append(statement)
        return self.responses.pop(0)


class _SessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def _db_with_session(session):
    db_mock = Mock()
    db_mock.session_scope.return_value = _SessionContext(session)
    return db_mock


class _ClosingSessionContext:
    def __init__(self, session, *close_targets):
        self.session = session
        self.close_targets = close_targets

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        for target in self.close_targets:
            target.close()
        return False


class _CloseGuarded:
    def __init__(self, **values):
        object.__setattr__(self, "_values", values)
        object.__setattr__(self, "_closed", False)

    def close(self):
        object.__setattr__(self, "_closed", True)

    def __getattribute__(self, name):
        if name in {"_values", "_closed", "close"}:
            return object.__getattribute__(self, name)
        if object.__getattribute__(self, "_closed"):
            raise AssertionError(f"{name} was accessed after session close")
        values = object.__getattribute__(self, "_values")
        if name in values:
            return values[name]
        raise AttributeError(name)


class ToolLifecycleEventModelTest(unittest.TestCase):
    def test_event_model_accepts_lifecycle_fields(self):
        event = ToolLifecycleEvent(
            project="demo",
            tool_name="hello",
            action="tool.publish",
            actor_type="user",
            actor_id="1",
            actor_name="Admin",
            version="v2",
            preview_key="abc",
            content_sha256="f" * 64,
            success=True,
            message="published",
            created_at=datetime(2026, 7, 6, 12, 0, 0),
        )

        self.assertEqual(event.project, "demo")
        self.assertEqual(event.tool_name, "hello")
        self.assertEqual(event.action, "tool.publish")
        self.assertTrue(event.success)

    def test_event_model_matches_lifecycle_event_schema_metadata(self):
        table = ToolLifecycleEvent.__table__

        self.assertEqual(table.name, "tool_lifecycle_events")
        self.assertIsInstance(table.c.id.type, BigInteger)
        self.assertIsNotNone(table.c.created_at.server_default)
        self.assertIn("CURRENT_TIMESTAMP", server_default_sql(table.c.created_at))
        self.assertEqual(server_default_sql(table.c.actor_id), "''")
        self.assertEqual(server_default_sql(table.c.actor_name), "''")
        self.assertEqual(server_default_sql(table.c.success), "TRUE")

        index_columns = {
            index.name: tuple(column.name for column in index.columns)
            for index in table.indexes
        }

        self.assertEqual(
            index_columns,
            {
                "idx_tle_tool": ("project", "tool_name"),
                "idx_tle_action": ("action",),
                "idx_tle_actor": ("actor_type", "actor_id"),
                "idx_tle_version": ("version",),
                "idx_tle_preview_key": ("preview_key",),
                "idx_tle_created_at": ("created_at",),
            },
        )


class LifecycleResultTest(unittest.TestCase):
    def test_success_result_shape(self):
        result = lifecycle_success(message="ok", data={"version": "v1"})

        self.assertIsInstance(result, LifecycleResult)
        self.assertTrue(result.success)
        self.assertEqual(result.code, "ok")
        self.assertEqual(result.message, "ok")
        self.assertEqual(result.next_action, "")
        self.assertEqual(result.data, {"version": "v1"})
        self.assertEqual(
            result.to_dict(),
            {
                "success": True,
                "code": "ok",
                "message": "ok",
                "next_action": "",
                "version": "v1",
            },
        )

    def test_error_result_shape(self):
        result = lifecycle_error(
            code="permission_denied",
            message="缺少权限",
            next_action="request_scope",
            data={"scope": "tool:publish"},
        )

        self.assertIsInstance(result, LifecycleResult)
        self.assertFalse(result.success)
        self.assertEqual(result.code, "permission_denied")
        self.assertEqual(result.message, "缺少权限")
        self.assertEqual(result.next_action, "request_scope")
        self.assertEqual(result.data, {"scope": "tool:publish"})
        self.assertEqual(
            result.to_dict(),
            {
                "success": False,
                "code": "permission_denied",
                "message": "缺少权限",
                "next_action": "request_scope",
                "scope": "tool:publish",
            },
        )

    def test_error_result_envelope_fields_win_over_data(self):
        result = lifecycle_error(
            code="permission_denied",
            message="缺少权限",
            next_action="request_scope",
            data={
                "success": True,
                "code": "ok",
                "message": "bad",
                "next_action": "bad",
                "detail": "x",
            },
        )

        self.assertEqual(
            result.to_dict(),
            {
                "success": False,
                "code": "permission_denied",
                "message": "缺少权限",
                "next_action": "request_scope",
                "detail": "x",
            },
        )

    def test_build_event_copies_actor_and_context(self):
        actor = Actor(type="token", id="9", name="Agent", scopes={"tool:publish"})
        event = _build_event(
            actor=actor,
            project="demo",
            tool_name="hello",
            action="tool.publish",
            success=True,
            message="published",
            version="v2",
            preview_key="preview-1",
            content_sha256="a" * 64,
        )

        self.assertIsInstance(event, ToolLifecycleEvent)
        self.assertEqual(event.project, "demo")
        self.assertEqual(event.tool_name, "hello")
        self.assertEqual(event.action, "tool.publish")
        self.assertEqual(event.actor_type, "token")
        self.assertEqual(event.actor_id, "9")
        self.assertEqual(event.actor_name, "Agent")
        self.assertEqual(event.version, "v2")
        self.assertEqual(event.preview_key, "preview-1")
        self.assertEqual(event.content_sha256, "a" * 64)
        self.assertTrue(event.success)
        self.assertEqual(event.message, "published")

    @patch("service.tool_lifecycle_service.logger")
    @patch("service.tool_lifecycle_service.db_manager")
    def test_record_lifecycle_event_swallows_persistence_errors(
        self,
        db_mock,
        logger_mock,
    ):
        db_mock.session_scope.side_effect = RuntimeError("database unavailable")

        record_lifecycle_event(
            actor=Actor(type="token", id="9", name="Agent", scopes={"tool:publish"}),
            project="demo",
            tool_name="hello",
            action="tool.publish",
            success=True,
            message="published",
        )

        logger_mock.exception.assert_called_once()


class LifecycleScopeTest(unittest.TestCase):
    def test_check_scope_returns_none_when_scope_exists(self):
        actor = Actor(type="token", id="9", name="Agent", scopes={"tool:publish"})

        self.assertIsNone(_check_scope(actor, "tool:publish"))

    def test_check_scope_returns_permission_denied_result_when_missing(self):
        actor = Actor(type="token", id="9", name="Agent", scopes={"tool:read"})

        result = _check_scope(actor, "tool:publish")

        self.assertIsInstance(result, LifecycleResult)
        self.assertFalse(result.success)
        self.assertEqual(result.code, "permission_denied")
        self.assertEqual(result.message, "缺少权限: tool:publish")
        self.assertEqual(result.next_action, "request_scope")


class LifecycleWriteTest(unittest.TestCase):
    def setUp(self):
        self.actor = system_actor("test")

    @patch("service.tool_lifecycle_service.delete_tool_from_db")
    @patch("service.tool_lifecycle_service.record_lifecycle_event")
    @patch("service.tool_lifecycle_service.create_temporary_preview")
    def test_preview_tool_only_creates_temporary_preview(
        self,
        preview_mock,
        event_mock,
        delete_db_mock,
    ):
        preview_mock.return_value = {
            "success": True,
            "key": "abc",
            "url": "/client/tool/abc",
            "message": "上传成功",
        }

        result = preview_tool(self.actor, "print(1)", project="demo", name="hello")

        self.assertTrue(result.success)
        self.assertEqual(result.data["key"], "abc")
        self.assertEqual(result.data["url"], "/client/tool/abc")
        preview_mock.assert_called_once_with("print(1)")
        delete_db_mock.assert_not_called()
        event_mock.assert_not_called()

    @patch("service.tool_lifecycle_service.record_lifecycle_event")
    @patch("service.tool_lifecycle_service.create_temporary_preview")
    def test_preview_tool_does_not_record_lifecycle_identity(
        self,
        preview_mock,
        event_mock,
    ):
        preview_mock.return_value = {
            "success": True,
            "key": "abc",
            "url": "/client/tool/abc",
            "message": "上传成功",
        }

        result = preview_tool(
            self.actor,
            "print(1)",
            project="Demo Project",
            name="Hello World",
        )

        self.assertTrue(result.success)
        event_mock.assert_not_called()

    @patch("service.tool_lifecycle_service.delete_tool_from_db")
    @patch("service.tool_lifecycle_service.record_lifecycle_event")
    @patch("service.tool_lifecycle_service.tool_manage_service.delete_tool")
    def test_delete_tool_records_success(
        self,
        delete_mock,
        event_mock,
        delete_db_mock,
    ):
        delete_mock.return_value = {"success": True}
        delete_db_mock.return_value = True

        result = delete_tool(self.actor, "demo", "hello")

        self.assertTrue(result.success)
        delete_mock.assert_called_once_with("demo", "hello")
        delete_db_mock.assert_called_once_with("demo", "hello.py")
        event_mock.assert_called_once_with(
            actor=self.actor,
            project="demo",
            tool_name="hello",
            action="tool.delete",
            success=True,
            message="工具已删除",
        )

    @patch("service.tool_lifecycle_service.delete_tool_from_db")
    @patch("service.tool_lifecycle_service.record_lifecycle_event")
    @patch("service.tool_lifecycle_service.tool_manage_service.delete_tool")
    def test_delete_tool_returns_error_when_index_delete_fails(
        self,
        delete_mock,
        event_mock,
        delete_db_mock,
    ):
        low_level_result = {"success": True}
        delete_mock.return_value = low_level_result
        delete_db_mock.return_value = False

        result = delete_tool(self.actor, "demo-project", "hello-world")

        self.assertFalse(result.success)
        self.assertEqual(result.code, "index_delete_failed")
        self.assertEqual(result.next_action, "retry_delete_index")
        self.assertIs(result.data, low_level_result)
        delete_mock.assert_called_once_with("demo-project", "hello-world")
        delete_db_mock.assert_called_once_with("demo-project", "hello-world.py")
        event_mock.assert_called_once_with(
            actor=self.actor,
            project="demo-project",
            tool_name="hello-world",
            action="tool.delete",
            success=False,
            message="工具 DB 索引删除失败",
        )

    @patch("service.tool_lifecycle_service.record_lifecycle_event")
    @patch("service.tool_lifecycle_service.get_tool_storage")
    def test_restore_runtime_cache_records_success(
        self,
        storage_mock,
        event_mock,
    ):
        storage_mock.return_value.restore_current_to_local.return_value = (
            "/tmp/hello.py"
        )

        result = restore_runtime_cache(self.actor, "demo", "hello")

        self.assertTrue(result.success)
        self.assertEqual(result.data["path"], "/tmp/hello.py")
        storage_mock.return_value.restore_current_to_local.assert_called_once_with(
            "demo",
            "hello",
        )
        event_mock.assert_called_once_with(
            actor=self.actor,
            project="demo",
            tool_name="hello",
            action="tool.restore_runtime_cache",
            success=True,
            message="运行缓存已恢复",
        )

    @patch("service.tool_lifecycle_service.record_lifecycle_event")
    @patch("service.tool_lifecycle_service.get_tool_storage")
    def test_restore_runtime_cache_uses_validated_identity(
        self,
        storage_mock,
        event_mock,
    ):
        storage = Mock()
        storage.restore_current_to_local.return_value = "/tmp/hello.py"
        storage_mock.return_value = storage

        result = restore_runtime_cache(self.actor, "demo-project", "hello-world")

        self.assertTrue(result.success)
        storage.restore_current_to_local.assert_called_once_with(
            "demo-project",
            "hello-world",
        )
        event_mock.assert_called_once_with(
            actor=self.actor,
            project="demo-project",
            tool_name="hello-world",
            action="tool.restore_runtime_cache",
            success=True,
            message="运行缓存已恢复",
        )

    @patch("service.tool_lifecycle_service.record_lifecycle_event")
    @patch("service.tool_lifecycle_service.tool_manage_service.delete_tool")
    def test_delete_tool_permission_denied_does_not_record_event(
        self,
        delete_mock,
        event_mock,
    ):
        actor = Actor(type="token", id="t1", name="readonly", scopes={"tool:read"})

        result = delete_tool(actor, "demo", "hello")

        self.assertFalse(result.success)
        self.assertEqual(result.code, "permission_denied")
        self.assertEqual(result.next_action, "request_scope")
        delete_mock.assert_not_called()
        event_mock.assert_not_called()


class LifecycleVersionActionTest(unittest.TestCase):
    def setUp(self):
        self.actor = system_actor("test")

    @patch("service.tool_lifecycle_service.record_lifecycle_event")
    @patch("service.tool_lifecycle_service.get_tool_storage")
    def test_publish_tool_uploads_content_without_existing_index(
        self,
        storage_factory_mock,
        event_mock,
    ):
        storage_mock = Mock()
        storage_mock.save_current.return_value = {
            "success": True,
            "version": "v1",
            "content_sha256": "e" * 64,
        }
        storage_mock.restore_current_to_local.return_value = "/app/tools/demo/chart.py"
        storage_factory_mock.return_value = storage_mock

        content = "def main():\n    print('uploaded')\n"
        result = publish_tool(
            self.actor,
            "demo",
            "chart",
            content=content,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.data["version"], "v1")
        self.assertEqual(result.data["url"], "/user/tools/demo/chart")
        self.assertEqual(result.data["local_path"], "/app/tools/demo/chart.py")
        storage_mock.save_current.assert_called_once_with(
            "demo",
            "chart",
            content,
            created_by="test",
        )
        storage_mock.restore_current_to_local.assert_called_once_with("demo", "chart")
        event_mock.assert_called_once_with(
            actor=self.actor,
            project="demo",
            tool_name="chart",
            action="tool.publish",
            success=True,
            message="工具已发布",
            version="v1",
            content_sha256="e" * 64,
        )

    @patch("service.tool_lifecycle_service.record_lifecycle_event")
    def test_publish_tool_rejects_content_without_main(self, event_mock):
        result = publish_tool(
            self.actor,
            "demo",
            "legacy",
            content="print('legacy')\n",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.code, "invalid_content")
        self.assertEqual(result.next_action, "add_main")
        self.assertIn("main()", result.message)
        event_mock.assert_called_once()

    @patch("service.tool_lifecycle_service.record_lifecycle_event")
    @patch("service.tool_lifecycle_service.tool_version_service.rollback_tool")
    @patch("service.tool_lifecycle_service.db_manager")
    def test_rollback_tool_records_new_version_with_source_version(
        self,
        db_mock,
        rollback_mock,
        event_mock,
    ):
        tool = Mock(id=43, project="demo", filename="hello.py")
        session = _FakeSession([_ExecResult(first=tool)])
        db_mock.session_scope.return_value = _SessionContext(session)
        rollback_mock.return_value = {
            "success": True,
            "version": "v5",
            "tool": {"project": "demo", "filename": "hello.py"},
        }

        result = rollback_tool(self.actor, "demo", "hello", "v2")

        self.assertTrue(result.success)
        self.assertEqual(result.data["source_version"], "v2")
        self.assertEqual(result.data["version"], "v5")
        rollback_mock.assert_called_once_with(43, "v2")
        event_mock.assert_called_once_with(
            actor=self.actor,
            project="demo",
            tool_name="hello",
            action="tool.rollback",
            success=True,
            message="工具已回滚",
            version="v5",
        )

    @patch("service.tool_lifecycle_service.logger")
    @patch("service.tool_lifecycle_service.record_lifecycle_event")
    @patch("service.tool_lifecycle_service.tool_version_service.rollback_tool")
    @patch("service.tool_lifecycle_service.db_manager")
    def test_rollback_tool_returns_stable_error_when_version_service_raises(
        self,
        db_mock,
        rollback_mock,
        event_mock,
        logger_mock,
    ):
        tool = Mock(id=43, project="demo", filename="hello.py")
        session = _FakeSession([_ExecResult(first=tool)])
        db_mock.session_scope.return_value = _SessionContext(session)
        rollback_mock.side_effect = RuntimeError("rollback unavailable")

        result = rollback_tool(self.actor, "demo", "hello", "v2")

        self.assertFalse(result.success)
        self.assertEqual(result.code, "rollback_failed")
        self.assertEqual(result.next_action, "inspect_versions")
        self.assertEqual(result.data["source_version"], "v2")
        self.assertEqual(result.data["error"], "rollback unavailable")
        logger_mock.exception.assert_called_once_with("工具回滚失败")
        event_mock.assert_called_once_with(
            actor=self.actor,
            project="demo",
            tool_name="hello",
            action="tool.rollback",
            success=False,
            message="rollback unavailable",
            version="v2",
        )

    @patch("service.tool_lifecycle_service.db_manager", None)
    def test_get_tool_state_without_db_returns_error(self):
        result = get_tool_state(self.actor, "demo", "hello")

        self.assertFalse(result.success)
        self.assertEqual(result.code, "database_unavailable")

    @patch("service.tool_lifecycle_service.db_manager", None)
    def test_list_tool_events_without_db_returns_empty_list(self):
        result = list_tool_events(self.actor, "demo", "hello")

        self.assertTrue(result.success)
        self.assertEqual(result.data["events"], [])

    @patch("service.tool_lifecycle_service.get_tool_storage")
    @patch("service.tool_lifecycle_service.db_manager")
    def test_publish_tool_permission_denied_skips_lookup(
        self,
        db_mock,
        publish_mock,
    ):
        actor = Actor(type="token", id="t1", name="readonly", scopes={"tool:read"})

        result = publish_tool(actor, "demo", "hello", "def main(): pass")

        self.assertFalse(result.success)
        self.assertEqual(result.code, "permission_denied")
        self.assertEqual(result.next_action, "request_scope")
        db_mock.session_scope.assert_not_called()
        publish_mock.assert_not_called()

    @patch("service.tool_lifecycle_service.db_manager")
    def test_list_tool_events_permission_denied_skips_lookup(self, db_mock):
        actor = Actor(type="token", id="t1", name="writer", scopes={"tool:publish"})

        result = list_tool_events(actor, "demo", "hello")

        self.assertFalse(result.success)
        self.assertEqual(result.code, "permission_denied")
        self.assertEqual(result.next_action, "request_scope")
        db_mock.session_scope.assert_not_called()

    @patch("service.tool_lifecycle_service.db_manager")
    def test_get_tool_state_returns_metadata_state_and_version_count(self, db_mock):
        updated_at = datetime(2026, 7, 6, 12, 0, 0)
        published_at = datetime(2026, 7, 6, 12, 30, 0)
        tool = Mock(
            id=42,
            project="demo",
            filename="hello.py",
            display_name="Hello",
            description="Demo tool",
            creator="tester",
            current_version="v3",
            tags="demo",
            created_at=datetime(2026, 7, 6, 11, 0, 0),
            updated_at=updated_at,
            published_at=published_at,
        )
        session = _FakeSession(
            [
                _ExecResult(first=tool),
                _ExecResult(all_rows=[Mock(version="v1"), Mock(version="v2")]),
            ]
        )
        db_mock.session_scope.return_value = _SessionContext(session)

        result = get_tool_state(self.actor, "demo", "hello")

        self.assertTrue(result.success)
        self.assertEqual(result.data["tool"]["id"], 42)
        self.assertEqual(result.data["tool"]["name"], "hello")
        self.assertEqual(result.data["tool"]["updated_at"], updated_at.isoformat())
        self.assertTrue(result.data["state"]["indexed"])
        self.assertTrue(result.data["state"]["published"])
        self.assertEqual(result.data["versions_count"], 2)

    @patch("service.tool_lifecycle_service.db_manager")
    def test_get_tool_state_serializes_before_session_close(self, db_mock):
        updated_at = datetime(2026, 7, 6, 12, 0, 0)
        published_at = datetime(2026, 7, 6, 12, 30, 0)
        tool = _CloseGuarded(
            id=42,
            project="demo",
            filename="hello.py",
            display_name="Hello",
            description="Demo tool",
            creator="tester",
            current_version="v3",
            tags="demo",
            created_at=datetime(2026, 7, 6, 11, 0, 0),
            updated_at=updated_at,
            published_at=published_at,
        )
        session = _FakeSession(
            [
                _ExecResult(first=tool),
                _ExecResult(all_rows=[Mock(version="v1")]),
            ]
        )
        db_mock.session_scope.return_value = _ClosingSessionContext(session, tool)

        result = get_tool_state(self.actor, "demo", "hello")

        self.assertTrue(result.success)
        self.assertEqual(result.data["tool"]["id"], 42)
        self.assertEqual(result.data["tool"]["updated_at"], updated_at.isoformat())
        self.assertEqual(result.data["versions_count"], 1)

    @patch("service.tool_lifecycle_service.db_manager")
    def test_list_tool_events_serializes_newest_first_and_caps_limit(self, db_mock):
        newest = ToolLifecycleEvent(
            id=2,
            project="demo-project",
            tool_name="hello-world",
            action="tool.publish",
            actor_type="system",
            actor_id="test",
            actor_name="test",
            version="v2",
            success=True,
            message="ok",
            created_at=datetime(2026, 7, 6, 12, 1, 0),
        )
        older = ToolLifecycleEvent(
            id=1,
            project="demo-project",
            tool_name="hello-world",
            action="tool.rollback",
            actor_type="system",
            actor_id="test",
            actor_name="test",
            version="v1",
            success=True,
            message="ok",
            created_at=datetime(2026, 7, 6, 12, 0, 0),
        )
        session = _FakeSession([_ExecResult(all_rows=[newest, older])])
        db_mock.session_scope.return_value = _SessionContext(session)

        result = list_tool_events(self.actor, "demo-project", "hello-world", limit=999)

        self.assertTrue(result.success)
        self.assertEqual(
            [event["id"] for event in result.data["events"]],
            [2, 1],
        )
        self.assertEqual(result.data["events"][0]["project"], "demo-project")
        self.assertEqual(result.data["events"][0]["tool_name"], "hello-world")
        compiled = session.statements[0].compile()
        self.assertIn("demo-project", compiled.params.values())
        self.assertIn("hello-world", compiled.params.values())
        self.assertEqual(session.statements[0]._limit_clause.value, 200)

    @patch("service.tool_lifecycle_service.db_manager")
    def test_list_tool_events_serializes_before_session_close(self, db_mock):
        event = _CloseGuarded(
            id=2,
            project="demo",
            tool_name="hello",
            action="tool.publish",
            actor_type="system",
            actor_id="test",
            actor_name="test",
            version="v2",
            preview_key=None,
            content_sha256=None,
            success=True,
            message="ok",
            created_at=datetime(2026, 7, 6, 12, 1, 0),
        )
        session = _FakeSession([_ExecResult(all_rows=[event])])
        db_mock.session_scope.return_value = _ClosingSessionContext(session, event)

        result = list_tool_events(self.actor, "demo", "hello")

        self.assertTrue(result.success)
        self.assertEqual(result.data["events"][0]["id"], 2)
        self.assertEqual(result.data["events"][0]["created_at"], "2026-07-06T12:01:00")


class AdminWorkspaceHelperTest(unittest.TestCase):
    def test_version_belongs_to_tool_matches_only_tool_id(self):
        tool = Tool(id=42, project="demo", filename="hello.py")
        stale_version = ToolVersion(
            id=7,
            tool_id=99,
            version="v7",
            content="stale",
            content_sha256="c" * 64,
        )
        matching_version = ToolVersion(
            id=8,
            tool_id=42,
            version="v8",
            content="current",
            content_sha256="d" * 64,
        )

        self.assertFalse(
            admin_tool_service._version_belongs_to_tool(tool, stale_version)
        )
        self.assertTrue(
            admin_tool_service._version_belongs_to_tool(tool, matching_version)
        )

    def test_tool_versions_statement_matches_only_tool_id(self):
        tool = Tool(id=42, project="demo", filename="hello.py")
        statement = admin_tool_service._tool_versions_statement(tool)

        compiled_sql = str(statement.compile(compile_kwargs={"literal_binds": True}))

        self.assertIn("tool_versions.tool_id = 42", compiled_sql)
        self.assertNotIn("tool_versions.tool_id IS NULL", compiled_sql)

    @patch("service.admin_tool_service.db_manager", None)
    def test_get_tool_workspace_without_db_returns_error(self):
        result = admin_tool_service.get_tool_workspace(1)

        self.assertEqual(
            result,
            {"success": False, "error": "数据库连接不可用"},
        )

    @patch("service.admin_tool_service.db_manager")
    def test_get_tool_workspace_missing_tool_returns_useful_error(self, db_mock):
        session = Mock()
        session.get.return_value = None
        db_mock.session_scope.return_value = _SessionContext(session)

        result = admin_tool_service.get_tool_workspace(404)

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "工具不存在: ID=404")
        session.get.assert_called_once_with(Tool, 404)

    @patch("service.admin_tool_service.tool_lifecycle_service.get_tool_state")
    @patch("service.admin_tool_service.db_manager")
    def test_get_tool_workspace_aggregates_tool_versions_events_and_state(
        self,
        db_mock,
        state_mock,
    ):
        tool = Tool(
            id=42,
            project="demo",
            filename="hello.py",
            display_name="Hello",
            description="Demo tool",
            creator="tester",
            current_version="v2",
            tags="demo, lifecycle",
            created_at=datetime(2026, 7, 6, 10, 0, 0),
            updated_at=datetime(2026, 7, 6, 11, 0, 0),
            published_at=datetime(2026, 7, 6, 12, 0, 0),
        )
        versions = [
            ToolVersion(
                id=1,
                tool_id=42,
                version="v1",
                content="v1",
                content_sha256="a" * 64,
                content_size=2,
                status="published",
                created_by="tester",
                created_at=datetime(2026, 7, 6, 10, 5, 0),
                published_at=datetime(2026, 7, 6, 10, 5, 0),
            ),
            ToolVersion(
                id=2,
                tool_id=42,
                version="v2",
                content="v2",
                content_sha256="b" * 64,
                content_size=2,
                status="published",
                created_by="tester",
                created_at=datetime(2026, 7, 6, 11, 5, 0),
                published_at=datetime(2026, 7, 6, 11, 5, 0),
            ),
        ]
        events = [
            ToolLifecycleEvent(
                id=3,
                project="demo",
                tool_name="hello",
                action="tool.preview",
                actor_type="token",
                actor_id="agent",
                actor_name="Agent",
                version=None,
                preview_key="preview-3",
                success=True,
                message="previewed",
                created_at=datetime(2026, 7, 6, 12, 6, 0),
            ),
            ToolLifecycleEvent(
                id=2,
                project="demo",
                tool_name="hello",
                action="tool.publish",
                actor_type="system",
                actor_id="tester",
                actor_name="tester",
                version="v2",
                preview_key="preview-2",
                content_sha256="b" * 64,
                success=True,
                message="published",
                created_at=datetime(2026, 7, 6, 12, 5, 0),
            ),
            ToolLifecycleEvent(
                id=1,
                project="demo",
                tool_name="hello",
                action="tool.rollback",
                actor_type="system",
                actor_id="tester",
                actor_name="tester",
                version="v1",
                success=True,
                message="rolled back",
                created_at=datetime(2026, 7, 6, 10, 5, 0),
            ),
        ]
        session = Mock()
        session.get.return_value = tool
        session.exec.side_effect = [
            _ExecResult(all_rows=versions),
            _ExecResult(all_rows=events),
        ]
        db_mock.session_scope.return_value = _SessionContext(session)
        state_mock.return_value = lifecycle_success(
            message="ok",
            data={"state": {"indexed": True, "published": True}},
        )

        result = admin_tool_service.get_tool_workspace(42)

        self.assertTrue(result["success"])
        self.assertEqual(result["tool"]["id"], 42)
        self.assertEqual(result["tool"]["name"], "hello")
        self.assertEqual(result["state"], {"indexed": True, "published": True})
        self.assertEqual(
            [version["version"] for version in result["versions"]],
            ["v2", "v1"],
        )
        self.assertTrue(result["versions"][0]["is_current"])
        self.assertEqual([event["id"] for event in result["events"]], [2, 1])
        self.assertEqual(result["events"][0]["created_at"], "2026-07-06T12:05:00")
        self.assertEqual(result["events"][0]["action_label"], "发布版本")
        self.assertEqual(result["events"][0]["action_group"], "publish")
        self.assertEqual(result["events"][0]["actor_type_label"], "系统")
        self.assertEqual(result["events"][0]["success_label"], "成功")
        self.assertEqual(result["events"][0]["success_color"], "positive")
        self.assertEqual(result["events"][0]["content_sha256_short"], "bbbbbbbbbbbb")
        self.assertEqual(result["events"][0]["details"]["action"], "tool.publish")
        self.assertEqual(session.exec.call_args_list[1].args[0]._limit_clause.value, 20)
        state_mock.assert_called_once()
        actor, project, name = state_mock.call_args.args
        self.assertEqual(actor.name, "admin-workspace-read")
        self.assertEqual(project, "demo")
        self.assertEqual(name, "hello")

    def test_lifecycle_event_row_adds_readable_display_fields(self):
        event = ToolLifecycleEvent(
            id=9,
            project="demo",
            tool_name="hello",
            action="tool.rollback",
            actor_type="token",
            actor_id="agent-1",
            actor_name="Agent",
            version="v3",
            preview_key=None,
            content_sha256="c" * 64,
            success=False,
            message="rollback failed",
            created_at=datetime(2026, 7, 6, 12, 10, 0),
        )

        row = admin_tool_service._lifecycle_event_to_row(event)

        self.assertEqual(row["action_label"], "回滚失败")
        self.assertEqual(row["action_group"], "rollback")
        self.assertEqual(row["actor_type_label"], "Token")
        self.assertEqual(row["success_label"], "失败")
        self.assertEqual(row["success_color"], "negative")
        self.assertEqual(row["content_sha256_short"], "cccccccccccc")
        self.assertEqual(
            row["details"],
            {
                "action": "tool.rollback",
                "actor_id": "agent-1",
                "content_sha256": "c" * 64,
                "preview_key": None,
                "version": "v3",
            },
        )

    @patch("service.admin_tool_service.tool_lifecycle_service.get_tool_state")
    @patch("service.admin_tool_service.db_manager")
    def test_get_tool_workspace_serializes_before_session_close(
        self,
        db_mock,
        state_mock,
    ):
        tool = _CloseGuarded(
            id=42,
            project="demo",
            filename="hello.py",
            display_name="Hello",
            description="Demo tool",
            creator="tester",
            current_version="v1",
            tags="demo",
            created_at=datetime(2026, 7, 6, 10, 0, 0),
            updated_at=datetime(2026, 7, 6, 11, 0, 0),
            published_at=datetime(2026, 7, 6, 12, 0, 0),
        )
        version = _CloseGuarded(
            id=1,
            tool_id=42,
            version="v1",
            content_sha256="a" * 64,
            content_size=2,
            status="published",
            created_by="tester",
            created_at=datetime(2026, 7, 6, 10, 5, 0),
            published_at=datetime(2026, 7, 6, 10, 5, 0),
        )
        event = _CloseGuarded(
            id=1,
            project="demo",
            tool_name="hello",
            action="tool.publish",
            actor_type="system",
            actor_id="tester",
            actor_name="tester",
            version="v1",
            preview_key=None,
            content_sha256="a" * 64,
            success=True,
            message="published",
            created_at=datetime(2026, 7, 6, 12, 5, 0),
        )
        session = Mock()
        session.get.return_value = tool
        session.exec.side_effect = [
            _ExecResult(all_rows=[version]),
            _ExecResult(all_rows=[event]),
        ]
        db_mock.session_scope.return_value = _ClosingSessionContext(
            session,
            tool,
            version,
            event,
        )
        state_mock.return_value = lifecycle_success(
            message="ok",
            data={"state": {"indexed": True}},
        )

        result = admin_tool_service.get_tool_workspace(42)

        self.assertTrue(result["success"])
        self.assertEqual(result["tool"]["updated_at"], "2026-07-06T11:00:00")
        self.assertEqual(result["versions"][0]["published_at"], "2026-07-06T10:05:00")
        self.assertEqual(result["events"][0]["message"], "published")


if __name__ == "__main__":
    unittest.main()
