import base64
import io
import json
import os
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from service.nicetool_environment_service import _render_device_authorization_block


class DeviceAuthorizationScriptTest(TestCase):
    def test_uses_installer_environment_urls_for_both_servers(self):
        for prefix in ("", "/purchaseadmin", "/other/nested"):
            with (
                self.subTest(prefix=prefix),
                tempfile.TemporaryDirectory() as directory,
            ):
                profiles = {
                    name: {
                        "url": f"https://{name}.example.com{prefix}",
                        "token_env": f"NICETOOL_{name.upper()}_TOKEN",
                    }
                    for name in ("test", "prod")
                }
                payload = base64.b64encode(
                    json.dumps({"environments": profiles}).encode()
                ).decode()
                script = _render_device_authorization_block(payload)
                code = script.split("python3 - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
                calls = []

                def respond(request, timeout, calls=calls, profiles=profiles):
                    calls.append(request.full_url)
                    name = "test" if "test.example.com" in request.full_url else "prod"
                    if request.full_url.endswith("/start"):
                        result = {
                            "user_code": "A+B/1234",
                            "device_code": "device",
                            "verification_uri_complete": "http://internal/auth/device/authorize",
                        }
                    else:
                        result = {
                            "status": "approved",
                            "token": "fixture-token",
                            "token_env": profiles[name]["token_env"],
                        }
                    return io.BytesIO(json.dumps(result).encode())

                credentials_path = Path(directory) / "credentials.env"
                with (
                    patch.dict(
                        os.environ,
                        {
                            "NICETOOL_INSTALL_PAYLOAD": payload,
                            "NICETOOL_INSTALL_PRODUCTION_ONLY": "0",
                            "NICETOOL_CREDENTIALS": str(credentials_path),
                        },
                    ),
                    patch("urllib.request.urlopen", side_effect=respond),
                    patch("webbrowser.open", return_value=True) as browser,
                    redirect_stdout(io.StringIO()),
                ):
                    exec(compile(code, "generated-authorization", "exec"), {})  # noqa: S102 — 仅执行本测试生成的受控代码，验证生成结果。
                self.assertEqual(
                    [call.args[0] for call in browser.call_args_list],
                    [
                        profile["url"] + "/auth/device/authorize?code=A%2BB%2F1234"
                        for profile in profiles.values()
                    ],
                )
                self.assertEqual(
                    calls,
                    [
                        profile["url"] + "/api/auth/device/" + action
                        for profile in profiles.values()
                        for action in ("start", "token")
                    ],
                )
                saved = credentials_path.read_text()
                for profile in profiles.values():
                    self.assertIn(profile["token_env"] + "=fixture-token", saved)
