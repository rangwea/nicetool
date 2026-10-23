import unittest
from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from models.auth import AuthUser, AuthUserResource
from service import access_control_service


class _Database:
    def __init__(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        for model in (AuthUser, AuthUserResource):
            model.__table__.create(self.engine)

    @contextmanager
    def session_scope(self):
        with Session(self.engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise


class AccessControlServiceTest(TestCase):
    def setUp(self):
        self.database = _Database()
        self.database_patch = patch.object(
            access_control_service, "db_manager", self.database
        )
        self.auth_patch = patch.object(
            access_control_service.auth_service, "is_enabled", return_value=True
        )
        self.database_patch.start()
        self.auth_patch.start()
        with self.database.session_scope() as session:
            user = AuthUser(subject="alice", username="alice", role="user")
            session.add(user)
            session.commit()
            session.refresh(user)
            self.user_id = user.id

    def tearDown(self):
        self.auth_patch.stop()
        self.database_patch.stop()
        self.database.engine.dispose()

    def test_admin_can_access_every_project(self):
        admin = AuthUser(id=99, subject="admin", username="admin", role="admin")

        self.assertIsNone(access_control_service.allowed_projects(admin))
        self.assertTrue(access_control_service.can_access_project(admin, "finance"))

    def test_user_gets_directly_granted_projects(self):
        access_control_service.update_user_projects(self.user_id, ["billing", "common"])
        user = AuthUser(id=self.user_id, subject="alice", username="alice", role="user")

        self.assertEqual(
            access_control_service.allowed_projects(user),
            {"billing", "common"},
        )
        self.assertEqual(
            access_control_service.get_user_projects(self.user_id),
            ["billing", "common"],
        )
        self.assertFalse(access_control_service.can_access_project(user, "legal"))

    def test_filter_tools_hides_unauthorized_projects(self):
        access_control_service.update_user_projects(self.user_id, ["billing"])
        user = AuthUser(id=self.user_id, subject="alice", username="alice", role="user")
        tools = [
            {"project": "billing", "name": "invoice"},
            {"project": "legal", "name": "contract"},
        ]

        self.assertEqual(
            access_control_service.filter_tools_for_user(tools, user),
            [{"project": "billing", "name": "invoice"}],
        )

    def test_user_without_resources_has_no_projects(self):
        user = AuthUser(id=self.user_id, subject="alice", username="alice", role="user")

        self.assertEqual(access_control_service.allowed_projects(user), set())

    def test_admin_grants_cannot_be_configured(self):
        with self.database.session_scope() as session:
            admin = AuthUser(subject="admin", username="admin", role="admin")
            session.add(admin)
            session.commit()
            session.refresh(admin)
            admin_id = admin.id

        with self.assertRaisesRegex(ValueError, "管理员自动拥有"):
            access_control_service.update_user_projects(admin_id, ["billing"])


if __name__ == "__main__":
    unittest.main()
