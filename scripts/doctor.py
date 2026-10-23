"""脱敏诊断：不读取 dotenv、Token、数据库密码或业务记录。"""

import argparse
import json
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def check_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise argparse.ArgumentTypeError("需要 http(s) 实例地址")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise argparse.ArgumentTypeError("地址不得包含凭据、查询参数或片段")
    return value.rstrip("/")


def diagnose(server: str) -> dict:
    report = {
        "python": platform.python_version(),
        "platform": platform.system(),
        "checks": [],
    }
    root = Path(__file__).resolve().parents[1]
    report["checks"].append(
        {
            "name": "project_files",
            "ok": all(
                (root / name).exists()
                for name in ("pyproject.toml", "uv.lock", "Dockerfile")
            ),
        }
    )
    docker = shutil.which("docker")
    if docker:
        try:
            result = subprocess.run(
                [docker, "compose", "version", "--short"],
                capture_output=True,
                timeout=10,
                check=False,
            )
            report["docker_compose_available"] = result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            report["docker_compose_available"] = False
    else:
        report["docker_compose_available"] = False
    # 不回显响应正文：业务代理可能返回内部配置或诊断堆栈。
    try:
        with urllib.request.urlopen(server + "/health", timeout=10) as response:
            body = response.read(32)
            ok = response.status == 200 and body.strip() == b"OK"
            report["checks"].append(
                {"name": "health", "ok": ok, "http_status": response.status}
            )
    except (OSError, ValueError, TypeError, AttributeError):
        report["checks"].append(
            {
                "name": "health",
                "ok": False,
                "hint": "检查实例是否启动、端口/挂载路径及数据库状态",
            }
        )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", type=check_url, default="http://localhost:8000")
    args = parser.parse_args()
    report = diagnose(args.server)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(check["ok"] for check in report["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main())
