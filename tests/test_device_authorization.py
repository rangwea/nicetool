from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from core.auth.service import AuthService
from models.auth import AuthDeviceAuthorization, AuthToken, AuthUser


class _Database:
    def __init__(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        for model in (AuthUser, AuthToken, AuthDeviceAuthorization):
            model.__table__.create(self.engine)

    @contextmanager
    def session_scope(self):
        with Session(self.engine) as session:
            yield session
            session.commit()


class DeviceAuthorizationTest(TestCase):
    def setUp(self):
        self.database = _Database()
        self.service = AuthService()
        self.database_patch = patch("core.auth.service.db_manager", self.database)
        self.database_patch.start()
        with self.database.session_scope() as session:
            user = AuthUser(
                provider="local", subject="alice", username="alice", is_active=True
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            self.user_id = user.id

    def tearDown(self):
        self.database_patch.stop()
        self.database.engine.dispose()

    def test_device_code_is_pending_then_exchanges_once_after_approval(self):
        grant = self.service.start_device_authorization("NICETOOL_TEST_TOKEN")

        self.assertEqual(
            self.service.exchange_device_authorization(grant["device_code"])["status"],
            "authorization_pending",
        )
        self.assertTrue(
            self.service.approve_device_authorization(grant["user_code"], self.user_id)
        )
        exchanged = self.service.exchange_device_authorization(grant["device_code"])
        self.assertEqual(exchanged["status"], "approved")
        self.assertTrue(exchanged["token"].startswith("nt_"))
        self.assertEqual(exchanged["token_env"], "NICETOOL_TEST_TOKEN")
        self.assertEqual(
            self.service.exchange_device_authorization(grant["device_code"])["status"],
            "invalid_grant",
        )

    def test_expired_device_code_cannot_be_approved(self):
        grant = self.service.start_device_authorization("NICETOOL_TEST_TOKEN")
        with self.database.session_scope() as session:
            record = session.get(AuthDeviceAuthorization, grant["id"])
            record.expires_at = datetime.now() - timedelta(seconds=1)
            session.add(record)

        self.assertFalse(
            self.service.approve_device_authorization(grant["user_code"], self.user_id)
        )

    def test_device_authorization_rejects_non_nicetool_variable(self):
        with self.assertRaisesRegex(ValueError, "Token 环境变量"):
            self.service.start_device_authorization("PATH")
