import os
import stat
import subprocess
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from models.nicetool_environment import (
    NiceToolEnvironment,
    NiceToolEnvironmentCreate,
    NiceToolEnvironmentUpdate,
)
from service import nicetool_environment_service as service


class _TestDatabase:
    def __init__(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        NiceToolEnvironment.__table__.create(self.engine)

    @contextmanager
    def session_scope(self):
        with Session(self.engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise


class NiceToolEnvironmentServiceTest(TestCase):
    def setUp(self) -> None:
        self.database = _TestDatabase()
        self.database_patch = patch.object(service, "db_manager", self.database)
        self.database_patch.start()

    def tearDown(self) -> None:
        self.database_patch.stop()
        self.database.engine.dispose()

    def create(self, name="test", **overrides):
        data = {
            "name": name,
            "url": f"https://{name}.example.com/",
            "token_env": f"NICETOOL_{name.upper()}_TOKEN",
            "is_default": name == "test",
            **overrides,
        }
        return service.create_environment(NiceToolEnvironmentCreate(**data))

    def test_crud_normalizes_and_switches_default(self):
        test = self.create()
        prod = self.create("prod", production=True, is_default=True)

        records = service.list_environments()
        self.assertEqual([item.name for item in records], ["test", "prod"])
        self.assertFalse(records[0].is_default)
        self.assertTrue(records[1].is_default)
        self.assertEqual(prod.url, "https://prod.example.com")

        with self.assertRaisesRegex(ValueError, "默认环境必须启用"):
            service.update_environment(
                prod.id, NiceToolEnvironmentUpdate(enabled=False)
            )
        self.assertTrue(service.delete_environment(test.id))

    def test_rejects_invalid_fields(self):
        cases = [
            {"name": "Test"},
            {"url": "example.com"},
            {"token_env": "token-value"},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.create(**overrides)

    def test_config_requires_enabled_default_and_never_contains_token_value(self):
        self.create(token_env="SUPER_SECRET_TOKEN")
        config = service.build_client_config()
        rendered = service.render_config_toml(config)

        self.assertEqual(config["default_environment"], "test")
        self.assertIn('token_env = "SUPER_SECRET_TOKEN"', rendered)
        self.assertNotIn("actual-secret", rendered)

        record = service.list_environments()[0]
        service.update_environment(
            record.id, NiceToolEnvironmentUpdate(is_default=False)
        )
        with self.assertRaisesRegex(ValueError, "默认环境"):
            service.build_client_config()

    def test_init_script_writes_atomically_and_protects_existing_file(self):
        self.create()
        self.create("prod", production=True, is_default=False)
        script = service.render_init_script()

        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "custom" / "config.toml"
            first = subprocess.run(
                ["sh", "-s", "--", "--config", str(config_path)],
                input=script,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            content = config_path.read_text()
            self.assertIn('default_environment = "test"', content)
            self.assertIn("[environments.prod]", content)
            self.assertEqual(stat.S_IMODE(config_path.stat().st_mode), 0o600)

            config_path.write_text("keep-me")
            refused = subprocess.run(
                ["sh", "-s", "--", "--config", str(config_path)],
                input=script,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(config_path.read_text(), "keep-me")

            forced = subprocess.run(
                ["sh", "-s", "--", "--config", str(config_path), "--force"],
                input=script,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(forced.returncode, 0, forced.stderr)
            self.assertIn("[environments.test]", config_path.read_text())

    def test_init_script_uses_xdg_config_home(self):
        self.create()
        script = service.render_init_script()
        with tempfile.TemporaryDirectory() as directory:
            environment = {**os.environ, "XDG_CONFIG_HOME": directory}
            result = subprocess.run(
                ["sh", "-s"],
                input=script,
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(Path(directory, "nicetool", "config.toml").is_file())

    def test_install_script_installs_skill_preserves_config_and_guides_token(self):
        config = {
            "default_environment": "test",
            "environments": {
                "test": {
                    "url": "https://test.example.com/nicetool",
                    "token_env": "NICETOOL_TEST_TOKEN",
                    "production": False,
                }
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            archive_path = root / "nicetool-skill.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("nicetool/SKILL.md", "---\nname: nicetool\n---\n")
                archive.writestr("nicetool/scripts/tool-cli.py", "print('ok')\n")
            init_path = root / "init.sh"
            init_path.write_text(
                "#!/bin/sh\n"
                '[ "$1" = "--config" ]\n'
                'mkdir -p "$(dirname "$2")"\n'
                'printf initialized > "$2"\n'
            )
            script = service.render_install_script(
                archive_path.as_uri(), init_path.as_uri(), config
            )
            environment = {
                **os.environ,
                "HOME": str(root / "home"),
                "XDG_CONFIG_HOME": str(root / "config"),
            }

            installed = subprocess.run(
                ["sh", "-s", "--", "--target", str(project), "--skip-auth"],
                input=script,
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)
            self.assertTrue((project / ".agents/skills/nicetool/SKILL.md").is_file())
            self.assertEqual(
                (root / "config/nicetool/config.toml").read_text(), "initialized"
            )
            self.assertIn("已跳过浏览器授权", installed.stdout)

            refused = subprocess.run(
                ["sh", "-s", "--", "--target", str(project), "--skip-auth"],
                input=script,
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(
                (root / "config/nicetool/config.toml").read_text(), "initialized"
            )

            forced = subprocess.run(
                [
                    "sh",
                    "-s",
                    "--",
                    "--target",
                    str(project),
                    "--force",
                    "--skip-auth",
                ],
                input=script,
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
            self.assertEqual(forced.returncode, 0, forced.stderr)

            (root / "home").mkdir(exist_ok=True)
            for scope, destination in (
                ("--global", root / "home/.agents/skills/nicetool/SKILL.md"),
                ("--local", project / ".agents/skills/nicetool/SKILL.md"),
            ):
                with self.subTest(scope=scope):
                    result = subprocess.run(
                        ["sh", "-s", "--", scope, "--force", "--skip-auth"],
                        input=script,
                        text=True,
                        capture_output=True,
                        env=environment,
                        cwd=project,
                        start_new_session=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(destination.is_file())

            for arguments in ([], ["--local", "--global"]):
                result = subprocess.run(
                    ["sh", "-s", "--", *arguments, "--skip-auth"],
                    input=script,
                    text=True,
                    capture_output=True,
                    env=environment,
                    cwd=project,
                    start_new_session=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 2, result.stderr)

            # A controlling terminal is independent of stdin (curl | sh).
            import pty
            import select
            import time

            for choice in (b"1\n", b"2\n"):
                pid, terminal = pty.fork()
                if pid == 0:
                    result = subprocess.run(
                        ["sh", "-s", "--", "--force", "--skip-auth"],
                        input=script,
                        text=True,
                        env=environment,
                        cwd=project,
                        check=False,
                    )
                    os._exit(result.returncode)
                output = b""
                answered = False
                deadline = time.monotonic() + 10
                try:
                    while time.monotonic() < deadline:
                        if select.select([terminal], [], [], 0.1)[0]:
                            try:
                                chunk = os.read(terminal, 4096)
                            except OSError:
                                break
                            if not chunk:
                                break
                            output += chunk
                            if not answered and b"[1/2" in output:
                                os.write(terminal, choice)
                                answered = True
                        finished, status = os.waitpid(pid, os.WNOHANG)
                        if finished:
                            pid = None
                            self.assertEqual(
                                os.waitstatus_to_exitcode(status), 0, output
                            )
                            break
                    self.assertTrue(answered, output)
                    self.assertIn("NiceTool Skill 已安装到".encode(), output)
                finally:
                    os.close(terminal)
                    if pid is not None:
                        finished, status = os.waitpid(pid, os.WNOHANG)
                        if not finished:
                            os.kill(pid, 9)
                            os.waitpid(pid, 0)

        self.assertNotIn("actual-secret", script)

    def test_install_script_uses_browser_device_authorization(self):
        config = {
            "default_environment": "test",
            "environments": {
                "test": {
                    "url": "https://test.example.com/nicetool",
                    "token_env": "NICETOOL_TEST_TOKEN",
                    "production": False,
                }
            },
        }
        script = service.render_install_script(
            "https://test.example.com/skill.zip",
            "https://test.example.com/api/init.sh",
            config,
        )

        self.assertIn("/api/auth/device/start", script)
        self.assertIn("/api/auth/device/token", script)
        self.assertIn("credentials.env", script)
        self.assertIn("os.chmod(credentials_path, 0o600)", script)
