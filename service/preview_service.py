"""Tool preview storage helpers.

Preview code is stored under /tmp so it can be executed by the NiceGUI preview
route without persisting into the real tools directory. Temporary previews keep
their random token behavior; fixed previews use username/tool_name in the URL
and overwrite the same backing file on every upload.
"""

import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from core.logger import _PREVIEW_LOG_DIR, _TMP_DIR, get_preview_logger
from core.settings import settings
from service.tool_runtime import ToolEntryPointError, validate_tool_entrypoint

_PREVIEW_META_DIR = _TMP_DIR / "_meta"
_SAFE_PART_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")
_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def _slug(value: str, fallback: str) -> str:
    slug = _SAFE_PART_PATTERN.sub("-", value.strip()).strip("-._")
    return slug or fallback


def build_fixed_preview_key(username: str, tool_name: str) -> str:
    """Build a stable, filesystem-safe key for a username/tool_name preview."""
    raw = f"{username}\0{tool_name}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    user_slug = _slug(username, "user")
    tool_slug = _slug(tool_name, "tool")
    return f"fixed-{user_slug}-{tool_slug}-{digest}"


def validate_preview_key(preview_key: str) -> str | None:
    """Return a safe preview key or None when the path value is invalid."""
    if _KEY_PATTERN.fullmatch(preview_key):
        return preview_key
    return None


def get_preview_file(preview_key: str) -> Path:
    return _TMP_DIR / f"{preview_key}.py"


def get_preview_url(preview_key: str) -> str:
    return settings.path_for(f"/client/tool/{preview_key}")


def get_preview_log_url(preview_key: str) -> str:
    return settings.path_for(f"/api/tools/preview/log/{preview_key}")


def get_fixed_preview_log_url(username: str, tool_name: str) -> str:
    return settings.path_for(
        "/api/tools/preview/log/fixed/"
        f"{quote(username.strip(), safe='')}/{quote(tool_name.strip(), safe='')}"
    )


def get_fixed_preview_url(username: str, tool_name: str) -> str:
    return settings.path_for(
        "/client/tool/"
        f"{quote(username.strip(), safe='')}/{quote(tool_name.strip(), safe='')}"
    )


def _extract_title(code_file: Path) -> str:
    try:
        with open(code_file, encoding="utf-8") as f:
            first_lines = f.read(500)
        for line in first_lines.split("\n"):
            stripped = line.strip()
            if stripped.startswith("name:"):
                return stripped[5:].strip()
    except Exception:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        return ""
    return ""


def _write_metadata(preview_key: str, metadata: dict) -> None:
    _PREVIEW_META_DIR.mkdir(parents=True, exist_ok=True)
    meta_file = _PREVIEW_META_DIR / f"{preview_key}.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def _read_metadata(preview_key: str) -> dict:
    meta_file = _PREVIEW_META_DIR / f"{preview_key}.json"
    if not meta_file.exists():
        return {}
    try:
        with open(meta_file, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        return {}


def create_temporary_preview(content: str) -> dict:
    """Create a one-off token preview and return response metadata."""
    preview_key = uuid.uuid4().hex
    return save_preview(
        preview_key=preview_key,
        content=content,
        preview_type="temporary",
        url=get_preview_url(preview_key),
    )


def create_fixed_preview(username: str, tool_name: str, content: str) -> dict:
    """Create or replace the fixed preview for username/tool_name."""
    clean_username = username.strip()
    clean_tool_name = tool_name.strip()
    preview_key = build_fixed_preview_key(clean_username, clean_tool_name)
    return save_preview(
        preview_key=preview_key,
        content=content,
        preview_type="fixed",
        url=get_fixed_preview_url(clean_username, clean_tool_name),
        username=clean_username,
        tool_name=clean_tool_name,
    )


def save_preview(
    *,
    preview_key: str,
    content: str,
    preview_type: str,
    url: str,
    username: str | None = None,
    tool_name: str | None = None,
) -> dict:
    """Validate Python code, write the preview file, and update metadata."""
    preview_logger = get_preview_logger(preview_key)
    content = content.strip()
    if not content:
        preview_logger.error("预览代码校验失败: content 不能为空")
        return {"success": False, "status_code": 400, "error": "content 不能为空"}

    try:
        validate_tool_entrypoint(content)
    except SyntaxError as e:
        message = f"Python 语法错误: 第 {e.lineno} 行 - {e.msg}"
        preview_logger.error(f"预览代码校验失败: {message}")
        return {
            "success": False,
            "status_code": 400,
            "code": "invalid_syntax",
            "error": message,
            "message": message,
            "next_action": "fix_syntax",
            "line": e.lineno,
            "column": e.offset,
        }
    except ToolEntryPointError as e:
        message = str(e)
        preview_logger.error(f"预览代码校验失败: {message}")
        return {
            "success": False,
            "status_code": 400,
            "code": "missing_main",
            "error": message,
            "message": message,
            "next_action": "add_main",
        }

    _TMP_DIR.mkdir(parents=True, exist_ok=True)
    filepath = get_preview_file(preview_key)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        preview_logger.error(f"写入预览工具文件失败: {e}")
        return {"success": False, "status_code": 500, "error": f"写入临时文件失败: {e}"}

    now = datetime.now().isoformat(timespec="seconds")
    metadata = {
        "key": preview_key,
        "type": preview_type,
        "url": url,
        "username": username,
        "tool_name": tool_name,
        "updated_at": now,
    }
    _write_metadata(preview_key, metadata)
    preview_logger.info(
        f"预览工具已保存: key={preview_key}; type={preview_type}; file={filepath}"
    )
    return {
        "success": True,
        "key": preview_key,
        "url": url,
        "preview_url": url,
        "log_url": get_preview_log_url(preview_key),
        "message": "预览已更新，刷新固定预览页面即可查看最新代码"
        if preview_type == "fixed"
        else "上传成功，访问 url 即可预览工具",
    }


def list_previews() -> list[dict]:
    """Return preview files with code/log metadata for API and admin pages."""
    if not _TMP_DIR.exists():
        return []

    previews = []
    for code_file in sorted(
        _TMP_DIR.glob("*.py"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        preview_key = code_file.stem
        log_file = _PREVIEW_LOG_DIR / f"{preview_key}.log"

        try:
            py_stat = code_file.stat()
            metadata = _read_metadata(preview_key)
            preview_type = metadata.get("type") or (
                "fixed" if preview_key.startswith("fixed-") else "temporary"
            )
            title = _extract_title(code_file)
            username = metadata.get("username")
            tool_name = metadata.get("tool_name")
            url = metadata.get("url") or get_preview_url(preview_key)

            previews.append(
                {
                    "key": preview_key,
                    "token": preview_key,
                    "type": preview_type,
                    "username": username,
                    "tool_name": tool_name,
                    "title": title or tool_name or "",
                    "url": url,
                    "file_size": py_stat.st_size,
                    "created_at": datetime.fromtimestamp(py_stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "has_log": log_file.exists(),
                    "log_size": log_file.stat().st_size if log_file.exists() else 0,
                }
            )
        except Exception:  # noqa: S112, BLE001 — 单个损坏预览不影响其余预览列表。 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            continue

    return previews


def read_preview_code(preview_key: str) -> str | None:
    code_file = get_preview_file(preview_key)
    if not code_file.exists():
        return None
    with open(code_file, encoding="utf-8") as f:
        return f.read()


def get_preview_log_file(preview_key: str) -> Path:
    return _PREVIEW_LOG_DIR / f"{preview_key}.log"


def fixed_preview_key_from_path(username: str, tool_name: str) -> str:
    return build_fixed_preview_key(username.strip(), tool_name.strip())
