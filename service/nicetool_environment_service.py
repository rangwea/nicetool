"""NiceTool 环境管理与客户端初始化脚本生成。"""

import base64
import json
import re
from datetime import UTC, datetime
from urllib.parse import urlsplit, urlunsplit

from sqlmodel import select

from core.database import db_manager
from core.logger import get_logger
from models.nicetool_environment import (
    NiceToolEnvironment,
    NiceToolEnvironmentCreate,
    NiceToolEnvironmentResponse,
    NiceToolEnvironmentUpdate,
)

logger = get_logger(__name__)

NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
TOKEN_ENV_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]*$")


def resolve_external_base_url(
    request_base_url: str, project_path: str, config: dict
) -> str:
    """使用登记的外部地址，保留反向代理之外的协议与部署前缀。"""
    request_base_url = request_base_url.rstrip("/")
    request_host = urlsplit(request_base_url).hostname
    for environment in config["environments"].values():
        environment_url = environment["url"].rstrip("/")
        if urlsplit(environment_url).hostname == request_host:
            return environment_url
    if project_path and urlsplit(request_base_url).path.rstrip("/") != project_path:
        return request_base_url + project_path
    return request_base_url


def _normalize_name(value: str) -> str:
    value = value.strip()
    if not NAME_PATTERN.fullmatch(value):
        raise ValueError("环境名称只能包含小写字母、数字、下划线和连字符")
    return value


def _normalize_url(value: str) -> str:
    value = value.strip()
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("服务地址必须是完整的 HTTP 或 HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError("服务地址不能包含用户名或密码")
    path = parsed.path.rstrip("/")
    return urlunsplit(
        (parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment)
    )


def _normalize_token_env(value: str) -> str:
    value = value.strip()
    if not TOKEN_ENV_PATTERN.fullmatch(value):
        raise ValueError("Token 环境变量必须使用大写字母、数字和下划线")
    return value


def _response(record: NiceToolEnvironment) -> NiceToolEnvironmentResponse:
    return NiceToolEnvironmentResponse(**record.model_dump())


def _clear_default(session, except_id: int | None = None) -> None:
    statement = select(NiceToolEnvironment).where(
        NiceToolEnvironment.is_default.is_(True)
    )
    for record in session.exec(statement).all():
        if except_id is None or record.id != except_id:
            record.is_default = False
            record.updated_at = datetime.now(UTC).replace(tzinfo=None)
            session.add(record)


def create_environment(
    data: NiceToolEnvironmentCreate,
) -> NiceToolEnvironmentResponse:
    """创建一个客户端环境，并维护唯一默认环境。"""
    name = _normalize_name(data.name)
    url = _normalize_url(data.url)
    token_env = _normalize_token_env(data.token_env)
    if data.is_default and not data.enabled:
        raise ValueError("默认环境必须启用")
    with db_manager.session_scope() as session:
        if session.exec(
            select(NiceToolEnvironment).where(NiceToolEnvironment.name == name)
        ).first():
            raise ValueError(f"环境名称 '{name}' 已存在")
        if data.is_default:
            _clear_default(session)
        record = NiceToolEnvironment(
            **data.model_dump(exclude={"name", "url", "token_env", "remark"}),
            name=name,
            url=url,
            token_env=token_env,
            remark=data.remark.strip(),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return _response(record)


def list_environments(
    *, enabled_only: bool = False
) -> list[NiceToolEnvironmentResponse]:
    """按管理员定义的顺序列出环境。"""
    with db_manager.session_scope() as session:
        statement = select(NiceToolEnvironment)
        if enabled_only:
            statement = statement.where(NiceToolEnvironment.enabled.is_(True))
        statement = statement.order_by(
            NiceToolEnvironment.sort_order.asc(), NiceToolEnvironment.id.asc()
        )
        return [_response(record) for record in session.exec(statement).all()]


def update_environment(
    environment_id: int, data: NiceToolEnvironmentUpdate
) -> NiceToolEnvironmentResponse | None:
    """更新环境，并维护唯一默认环境。"""
    with db_manager.session_scope() as session:
        record = session.get(NiceToolEnvironment, environment_id)
        if not record:
            return None
        changes = data.model_dump(exclude_unset=True)
        if "name" in changes:
            changes["name"] = _normalize_name(changes["name"])
            duplicate = session.exec(
                select(NiceToolEnvironment).where(
                    NiceToolEnvironment.name == changes["name"],
                    NiceToolEnvironment.id != environment_id,
                )
            ).first()
            if duplicate:
                raise ValueError(f"环境名称 '{changes['name']}' 已存在")
        if "url" in changes:
            changes["url"] = _normalize_url(changes["url"])
        if "token_env" in changes:
            changes["token_env"] = _normalize_token_env(changes["token_env"])
        enabled = changes.get("enabled", record.enabled)
        is_default = changes.get("is_default", record.is_default)
        if is_default and not enabled:
            raise ValueError("默认环境必须启用")
        if changes.get("is_default"):
            _clear_default(session, environment_id)
        for key, value in changes.items():
            setattr(record, key, value.strip() if key == "remark" else value)
        record.updated_at = datetime.now(UTC).replace(tzinfo=None)
        session.add(record)
        session.commit()
        session.refresh(record)
        return _response(record)


def delete_environment(environment_id: int) -> bool:
    """删除环境。"""
    with db_manager.session_scope() as session:
        record = session.get(NiceToolEnvironment, environment_id)
        if not record:
            return False
        session.delete(record)
        session.commit()
        return True


def build_client_config() -> dict:
    """构建可公开下发的配置；只包含 Token 环境变量名。"""
    environments = list_environments(enabled_only=True)
    if not environments:
        raise ValueError("未配置启用的 NiceTool 环境")
    defaults = [item for item in environments if item.is_default]
    if len(defaults) != 1:
        raise ValueError("必须配置且只能配置一个启用的默认环境")
    return {
        "default_environment": defaults[0].name,
        "environments": {
            item.name: {
                "url": item.url,
                "token_env": item.token_env,
                "production": item.production,
            }
            for item in environments
        },
    }


def render_config_toml(config: dict | None = None) -> str:
    """渲染 NiceTool CLI 所使用的 TOML。"""
    config = config or build_client_config()
    lines = [
        f"default_environment = {json.dumps(config['default_environment'])}",
        "",
    ]
    for name, profile in config["environments"].items():
        lines.extend(
            [
                f"[environments.{name}]",
                f"url = {json.dumps(profile['url'])}",
                f"token_env = {json.dumps(profile['token_env'])}",
            ]
        )
        if profile.get("production"):
            lines.append("production = true")
        lines.append("")
    return "\n".join(lines)


def render_init_script(config: dict | None = None) -> str:
    """生成独立运行、原子写入配置的 POSIX sh 脚本。"""
    payload = base64.b64encode(
        json.dumps(config or build_client_config(), separators=(",", ":")).encode()
    ).decode()
    return f"""#!/bin/sh
set -eu

CONFIG_PATH=""
FORCE=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --config)
            [ "$#" -ge 2 ] || {{ echo "nicetool init: --config 缺少路径" >&2; exit 2; }}
            CONFIG_PATH=$2
            shift 2
            ;;
        --force)
            FORCE=1
            shift
            ;;
        -h|--help)
            echo "用法: sh [--config PATH] [--force]"
            exit 0
            ;;
        *)
            echo "nicetool init: 未知参数: $1" >&2
            exit 2
            ;;
    esac
done

export NICETOOL_INIT_PAYLOAD='{payload}'
export NICETOOL_INIT_CONFIG_PATH="$CONFIG_PATH"
export NICETOOL_INIT_FORCE="$FORCE"
python3 - <<'PY'
import base64
import json
import os
import tempfile

payload = json.loads(base64.b64decode(os.environ["NICETOOL_INIT_PAYLOAD"]))
path = os.environ.get("NICETOOL_INIT_CONFIG_PATH")
if not path:
    root = os.environ.get("XDG_CONFIG_HOME") or os.path.join("~", ".config")
    path = os.path.join(root, "nicetool", "config.toml")
path = os.path.abspath(os.path.expanduser(path))
force = os.environ.get("NICETOOL_INIT_FORCE") == "1"
if os.path.exists(path) and not force:
    raise SystemExit("nicetool init: 配置已存在，使用 --force 覆盖: " + path)

def quote(value):
    return json.dumps(value, ensure_ascii=False)

lines = ["default_environment = " + quote(payload["default_environment"]), ""]
for name, profile in payload["environments"].items():
    lines.extend([
        "[environments." + name + "]",
        "url = " + quote(profile["url"]),
        "token_env = " + quote(profile["token_env"]),
    ])
    if profile.get("production"):
        lines.append("production = true")
    lines.append("")
content = "\\n".join(lines)

directory = os.path.dirname(path)
os.makedirs(directory, mode=0o700, exist_ok=True)
fd, temporary = tempfile.mkstemp(prefix=".config.toml.", dir=directory, text=True)
try:
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)
    os.chmod(path, 0o600)
except BaseException:
    try:
        os.unlink(temporary)
    except FileNotFoundError:
        pass
    raise
print("NiceTool 配置已写入: " + path)
PY
"""


def _render_device_authorization_block(
    payload: str, *, production_only: bool = False
) -> str:
    return f"""export NICETOOL_INSTALL_PAYLOAD='{payload}'
export NICETOOL_INSTALL_PRODUCTION_ONLY='{1 if production_only else 0}'
python3 - <<'PY'
import base64
import json
import os
import stat
import tempfile
import time
import urllib.request
from urllib.parse import quote
import webbrowser

payload = json.loads(base64.b64decode(os.environ["NICETOOL_INSTALL_PAYLOAD"]))
profiles = payload["environments"]
if os.environ.get("NICETOOL_INSTALL_PRODUCTION_ONLY") == "1":
    profiles = {{"prod": profiles["prod"]}} if "prod" in profiles else {{}}
if not profiles:
    raise SystemExit("nicetool install: 未配置可授权的正式服环境")

config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.join("~", ".config")
credentials_path = os.path.abspath(os.path.expanduser(
    os.environ.get("NICETOOL_CREDENTIALS")
    or os.path.join(config_home, "nicetool", "credentials.env")
))
credentials = {{}}
if os.path.isfile(credentials_path):
    with open(credentials_path, "r", encoding="utf-8") as source:
        for line in source:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                credentials[key.strip()] = value.strip()

def post_json(url, body):
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={{"Content-Type": "application/json"}},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

for name, profile in profiles.items():
    base_url = profile["url"].rstrip("/")
    started = post_json(
        base_url + "/api/auth/device/start", {{"token_env": profile["token_env"]}}
    )
    authorization_url = (
        base_url + "/auth/device/authorize?code=" + quote(started["user_code"], safe="")
    )
    print("请在浏览器确认 NiceTool 授权（" + name + "）:")
    print("  " + authorization_url)
    if not webbrowser.open(authorization_url):
        print("未能自动打开浏览器，请手动访问上方地址。")
    deadline = time.time() + int(started.get("expires_in", 600))
    interval = max(1, int(started.get("interval", 2)))
    while time.time() < deadline:
        result = post_json(
            base_url + "/api/auth/device/token",
            {{"device_code": started["device_code"]}},
        )
        if result.get("status") == "approved":
            credentials[result["token_env"]] = result["token"]
            print("授权成功: " + name)
            break
        if result.get("status") != "authorization_pending":
            raise SystemExit("nicetool install: 授权无效或已过期")
        time.sleep(interval)
    else:
        raise SystemExit("nicetool install: 等待浏览器授权超时")

directory = os.path.dirname(credentials_path)
os.makedirs(directory, mode=0o700, exist_ok=True)
fd, temporary = tempfile.mkstemp(prefix=".credentials.", dir=directory, text=True)
try:
    os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        for key in sorted(credentials):
            output.write(key + "=" + credentials[key] + "\\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, credentials_path)
    os.chmod(credentials_path, 0o600)
except BaseException:
    try:
        os.unlink(temporary)
    except FileNotFoundError:
        pass
    raise
print("NiceTool 凭据已保存: " + credentials_path)
print("请重新启动 AI Agent。")
PY
"""


def render_install_script(
    download_url: str,
    init_url: str,
    config: dict | None = None,
) -> str:
    """生成可选择项目或全局安装的 Skill 安装和授权脚本。"""
    payload = base64.b64encode(
        json.dumps(config or build_client_config(), separators=(",", ":")).encode()
    ).decode()
    return f"""#!/bin/sh
set -eu

TARGET="."
SCOPE=""
FORCE=0
SKIP_AUTH=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --local|--global)
            [ -z "$SCOPE" ] || {{ echo "nicetool install: 安装范围参数不能重复或组合使用" >&2; exit 2; }}
            SCOPE=${{1#--}}
            shift
            ;;
        --target)
            [ -z "$SCOPE" ] || {{ echo "nicetool install: 安装范围参数不能重复或组合使用" >&2; exit 2; }}
            SCOPE=local
            [ "$#" -ge 2 ] || {{ echo "nicetool install: --target 缺少路径" >&2; exit 2; }}
            TARGET=$2
            shift 2
            ;;
        --force)
            FORCE=1
            shift
            ;;
        --skip-auth)
            SKIP_AUTH=1
            shift
            ;;
        -h|--help)
            echo "用法: sh [--local | --global | --target PROJECT_PATH] [--force] [--skip-auth]"
            exit 0
            ;;
        *)
            echo "nicetool install: 未知参数: $1" >&2
            exit 2
            ;;
    esac
done

if [ -z "$SCOPE" ]; then
    if ( : </dev/tty ) 2>/dev/null; then
        while [ -z "$SCOPE" ]; do
            printf '安装位置：1) 当前目录  2) 全局 (~/.agents/skills)\n请选择 [1/2，默认 1]: ' >/dev/tty
            IFS= read -r choice </dev/tty || {{ echo "nicetool install: 未能读取安装位置" >&2; exit 2; }}
            case "$choice" in
                ""|1) SCOPE=local ;;
                2) SCOPE=global ;;
                *) echo "请输入 1 或 2。" >/dev/tty ;;
            esac
        done
    else
        echo "nicetool install: 无交互终端，请指定 --local、--global 或 --target PROJECT_PATH" >&2
        exit 2
    fi
fi
if [ "$SCOPE" = global ]; then
    TARGET="$HOME"
fi

command -v curl >/dev/null 2>&1 || {{ echo "nicetool install: 需要 curl" >&2; exit 1; }}
command -v python3 >/dev/null 2>&1 || {{ echo "nicetool install: 需要 python3" >&2; exit 1; }}
[ -d "$TARGET" ] || {{ echo "nicetool install: 目标项目不存在: $TARGET" >&2; exit 1; }}

TEMP_DIR=$(mktemp -d "${{TMPDIR:-/tmp}}/nicetool-install.XXXXXX")
trap 'rm -rf "$TEMP_DIR"' EXIT HUP INT TERM
ARCHIVE="$TEMP_DIR/nicetool-skill.zip"
curl -fsSL {json.dumps(download_url)} -o "$ARCHIVE"

export NICETOOL_INSTALL_ARCHIVE="$ARCHIVE"
export NICETOOL_INSTALL_TARGET="$TARGET"
export NICETOOL_INSTALL_FORCE="$FORCE"
python3 - <<'PY'
import os
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

archive_path = Path(os.environ["NICETOOL_INSTALL_ARCHIVE"])
project_path = Path(os.environ["NICETOOL_INSTALL_TARGET"]).expanduser().resolve()
force = os.environ.get("NICETOOL_INSTALL_FORCE") == "1"
destination = project_path / ".agents" / "skills" / "nicetool"
destination_parent = destination.parent
destination_parent.mkdir(parents=True, exist_ok=True)

if destination.exists() or destination.is_symlink():
    if not force:
        raise SystemExit(
            "nicetool install: Skill 已存在，使用 --force 替换: " + str(destination)
        )

staging_root = Path(tempfile.mkdtemp(prefix=".nicetool-stage.", dir=destination_parent))
backup = destination_parent / (".nicetool-backup." + str(os.getpid()))
try:
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            path = PurePosixPath(member.filename)
            if path.is_absolute() or ".." in path.parts:
                raise SystemExit("nicetool install: ZIP 包含不安全路径")
            if not path.parts or path.parts[0] != "nicetool":
                raise SystemExit("nicetool install: ZIP 根目录必须为 nicetool/")
        archive.extractall(staging_root)

    staged_skill = staging_root / "nicetool"
    if not (staged_skill / "SKILL.md").is_file():
        raise SystemExit("nicetool install: ZIP 缺少 nicetool/SKILL.md")

    if destination.exists() or destination.is_symlink():
        os.replace(destination, backup)
    try:
        os.replace(staged_skill, destination)
    except BaseException:
        if backup.exists() or backup.is_symlink():
            os.replace(backup, destination)
        raise
    if backup.is_symlink() or backup.is_file():
        backup.unlink()
    elif backup.exists():
        shutil.rmtree(backup)
finally:
    shutil.rmtree(staging_root, ignore_errors=True)

print("NiceTool Skill 已安装到: " + str(destination))
PY

CONFIG_PATH="${{NICETOOL_CONFIG:-${{XDG_CONFIG_HOME:-$HOME/.config}}/nicetool/config.toml}}"
if [ -f "$CONFIG_PATH" ]; then
    echo "NiceTool 环境配置已存在，保留: $CONFIG_PATH"
else
    curl -fsSL {json.dumps(init_url)} | sh -s -- --config "$CONFIG_PATH"
fi

if [ "$SKIP_AUTH" -eq 0 ]; then
{_render_device_authorization_block(payload)}
else
    echo "已跳过浏览器授权。"
fi
"""
