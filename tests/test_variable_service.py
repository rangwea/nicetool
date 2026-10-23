from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from core.variable_manager import VariableProxy
from models.variable import Variable, VariableCreate, VariableUpdate
from service import variable_service


class _TestDatabase:
    def __init__(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Variable.__table__.create(self.engine)

    @contextmanager
    def session_scope(self):
        with Session(self.engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise


class VariableServiceTest(TestCase):
    def setUp(self) -> None:
        self.database = _TestDatabase()
        self.database_patch = patch.object(
            variable_service,
            "db_manager",
            self.database,
        )
        self.database_patch.start()

    def tearDown(self) -> None:
        self.database_patch.stop()
        self.database.engine.dispose()

    def test_crud_and_tool_proxy(self):
        created = variable_service.create_variable(
            VariableCreate(key=" API_BASE ", value="https://example.com", remark="接口")
        )

        self.assertEqual(created.key, "API_BASE")
        self.assertEqual(VariableProxy()["API_BASE"], "https://example.com")
        self.assertEqual(VariableProxy().get("MISSING", "fallback"), "fallback")

        updated = variable_service.update_variable(
            created.id,
            VariableUpdate(value="https://new.example.com", remark="新接口"),
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.value, "https://new.example.com")
        self.assertEqual(len(variable_service.list_variables("新接口")), 1)
        keys = variable_service.list_variable_keys("API")
        self.assertEqual(keys, [{"key": "API_BASE", "remark": "新接口"}])
        self.assertNotIn("value", keys[0])

        self.assertTrue(variable_service.delete_variable(created.id))
        with self.assertRaisesRegex(KeyError, "变量不存在"):
            VariableProxy()["API_BASE"]

    def test_duplicate_key_is_rejected(self):
        variable_service.create_variable(VariableCreate(key="MODE", value="a"))

        with self.assertRaisesRegex(ValueError, "已存在"):
            variable_service.create_variable(VariableCreate(key="MODE", value="b"))
