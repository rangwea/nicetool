#!/usr/bin/env python3
"""
Tool CLI - 工具管理命令行工具

与 NiceTool 的 Tool API 交互，支持：
- 列出工具
- 查看工具内容
- 本地创建工具文件
- 发布工具
- 删除工具
- 预览工具
- 列出数据源
- 列出平台变量 Key
- 查看工具日志
- 查看预览日志

使用示例:
    # 列出所有工具
    python scripts/tool-cli.py list

    # 按项目过滤工具
    python scripts/tool-cli.py list --project demo

    # 查看工具内容
    python scripts/tool-cli.py get demo hello

    # 本地创建工具文件（从文件；不调用服务端 create）
    python scripts/tool-cli.py create demo my-tool --file ./my-tool.py --tags data,export

    # 本地创建工具文件（从 stdin）
    echo "..." | python scripts/tool-cli.py create demo my-tool --stdin

    # 发布工具（默认上传 tools/{project}/{name}.py 内容）
    python scripts/tool-cli.py publish demo hello

    # 从指定文件发布工具
    python scripts/tool-cli.py publish demo hello --file ./hello.py

    # 查看正式工具状态
    python scripts/tool-cli.py status demo hello

    # 删除工具
    python scripts/tool-cli.py delete demo hello

    # 固定预览工具（推荐给 Agent 生成流程）
    python scripts/tool-cli.py preview demo hello --file ./draft.py

    # 临时预览工具
    python scripts/tool-cli.py preview --file ./draft.py

    # 获取所有工具项目
    python scripts/tool-cli.py projects

    # 列出数据源
    python scripts/tool-cli.py databases

    # 按类型过滤数据源
    python scripts/tool-cli.py databases --type mysql

    # 列出可用平台变量 Key（不返回 Value）
    python scripts/tool-cli.py variables

    # 按 Key 或备注搜索平台变量
    python scripts/tool-cli.py variables --search api

    # 查看工具日志（列出所有有日志的工具）
    python scripts/tool-cli.py toollog

    # 查看指定工具日志
    python scripts/tool-cli.py toollog demo hello

    # 实时跟踪工具日志
    python scripts/tool-cli.py toollog demo hello -f

    # 搜索工具日志
    python scripts/tool-cli.py toollog demo hello -g "ERROR"

    # 查看预览日志（列出所有预览工具）
    python scripts/tool-cli.py prelog

    # 查看固定预览日志
    python scripts/tool-cli.py prelog demo hello

    # 查看指定 token 的预览日志
    python scripts/tool-cli.py prelog d6b7e3b1f90d45bc98e762fa02b15ab8

    # 实时跟踪预览日志
    python scripts/tool-cli.py prelog d6b7e3b1f90d45bc98e762fa02b15ab8 -f

    # 搜索预览日志
    python scripts/tool-cli.py prelog d6b7e3b1f90d45bc98e762fa02b15ab8 -g "ERROR"

    # 指定服务器地址（或用环境变量 NICETOOL_URL）
    python scripts/tool-cli.py --server http://localhost:8000 list

    # 从任意工作目录调用（脚本路径自解析，无需 cd 到 skill 目录）
    python /path/to/nicetool/scripts/tool-cli.py list

环境变量:
    NICETOOL_URL          服务端地址，等同 --server（未传 --server 时生效）
    NICETOOL_PROJECT_ROOT NiceTool 项目根目录（toollog 查 logs/tools，未设则向上查找 main.py）
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

# 本脚本与 skill 根目录（与 SKILL.md 同级），不依赖 cwd
SCRIPT_PATH = Path(__file__).resolve()
SKILL_ROOT = SCRIPT_PATH.parent.parent
sys.path.insert(0, str(SCRIPT_PATH.parent))

from nicetool_config import (
    ConfigError,
    resolve_runtime,
)


class ApiError(Exception):
    """服务端 API 错误，保留响应体供命令处理。"""

    def __init__(self, status_code: int, data: dict | None, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.data = data or {}


def build_public_url(server: str, path_or_url: str) -> str:
    """根据 API 基址和服务端返回路径构造页面 URL，避免重复 mount path。"""
    if not path_or_url:
        return server.rstrip("/")

    returned = urlsplit(path_or_url)
    if returned.scheme and returned.netloc:
        return path_or_url

    base = urlsplit(server.rstrip("/"))
    base_path = base.path.rstrip("/")
    returned_path = f"/{returned.path.lstrip('/')}"
    if base_path and (
        returned_path == base_path or returned_path.startswith(f"{base_path}/")
    ):
        final_path = returned_path
    else:
        final_path = f"{base_path}{returned_path}"

    return urlunsplit(
        (
            base.scheme,
            base.netloc,
            final_path,
            returned.query,
            returned.fragment,
        )
    )


def normalize_error_payload(data: dict | None) -> dict:
    """将服务端错误归一为稳定的 lifecycle-ish 响应形状。"""
    source = data or {}
    message = (
        source.get("message")
        or source.get("detail")
        or source.get("error")
        or "请求失败"
    )
    envelope = {
        "success": False,
        "code": source.get("code") or "request_failed",
        "message": message,
        "next_action": source.get("next_action") or "inspect_error",
    }
    reserved = {"success", "code", "message", "detail", "error", "next_action"}
    extras = {key: value for key, value in source.items() if key not in reserved}
    return {**extras, **envelope}


def validate_tool_identity(project: str, name: str) -> None:
    """独立分发的 CLI 使用与服务端一致的名称契约。"""
    for value, maximum in ((project, 100), (name, 197)):
        if (
            not isinstance(value, str)
            or not re.fullmatch(r"[a-z0-9_-]+", value)
            or len(value) > maximum
        ):
            raise ValueError(
                f"名称不合法: {value!r}；仅支持小写字母、数字、下划线和连字符，长度不超过 {maximum}"
            )


def resolve_project_root() -> Path:
    """解析 NiceTool 项目根（toollog 用 logs/tools）。--server 与项目根无关。"""
    env_root = os.environ.get("NICETOOL_PROJECT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    cwd = Path.cwd()
    for candidate in (cwd, *cwd.parents):
        if (candidate / "main.py").is_file():
            return candidate
        if (candidate / "logs" / "tools").is_dir():
            return candidate
    return cwd


def resolve_file_path(path: str) -> Path:
    """将 --file 路径解析为绝对路径（相对路径基于当前 cwd）。"""
    p = Path(path).expanduser()
    return p.resolve() if not p.is_absolute() else p


def make_request(
    url: str,
    method: str = "GET",
    data: dict | None = None,
    timeout: int = 30,
) -> dict:
    """发送 HTTP 请求"""
    headers = {"Content-Type": "application/json"}
    token = getattr(make_request, "token", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")

    request = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            error_data = json.loads(error_body)
            normalized_payload = normalize_error_payload(error_data)
            raise ApiError(e.code, normalized_payload, normalized_payload["message"])
        except json.JSONDecodeError:
            raise ApiError(e.code, None, f"HTTP {e.code}: {error_body}")
    except URLError as e:
        raise ConnectionError(f"连接失败: {e.reason}") from e


def make_raw_request(url: str, timeout: int = 30) -> tuple[int, str]:
    """发送 GET 请求，返回 (status_code, text)，不解析 JSON"""
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    headers = {"Accept": "text/plain, */*"}
    token = getattr(make_request, "token", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except URLError as e:
        return 0, f"连接失败: {e.reason}"


def print_table(headers: list[str], rows: list[list[str]]):
    """打印表格"""
    if not rows:
        print("(无数据)")
        return

    # 计算每列宽度
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    # 打印表头
    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))

    # 打印数据行
    for row in rows:
        print(" | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))


def cmd_list(args):
    """列出工具"""
    url = f"{args.server}/api/tools"
    if args.project:
        url += f"?project={args.project}"

    result = make_request(url)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    tools = result.get("tools", [])
    print(f"共 {result.get('total', len(tools))} 个工具\n")

    if tools:
        headers = ["项目", "名称", "标题", "描述", "创建时间"]
        rows = [
            [
                t.get("project", ""),
                t.get("name", ""),
                t.get("title", "")[:20],
                t.get("description", "")[:30],
                t.get("created_at", ""),
            ]
            for t in tools
        ]
        print_table(headers, rows)


def cmd_projects(args):
    """列出工具项目"""
    url = f"{args.server}/api/tools/projects"
    result = make_request(url)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    projects = result.get("projects", [])
    print(f"共 {len(projects)} 个项目:\n")
    for p in projects:
        print(f"  - {p}")


def cmd_get(args):
    """获取工具详情"""
    url = f"{args.server}/api/tools/{args.project}/{args.name}?content=true"
    result = make_request(url)

    meta = result.get("meta", {})
    content = result.get("content", "")

    if args.output:
        output_path = resolve_file_path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        if args.json:
            print(
                json.dumps(
                    {
                        "success": True,
                        "output": str(output_path),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        print(f"✓ 已写入: {output_path}")
        return

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"项目: {meta.get('project', '')}")
    print(f"名称: {meta.get('name', '')}")
    print(f"标题: {meta.get('title', '')}")
    print(f"描述: {meta.get('description', '')}")
    print(f"创建者: {meta.get('creator', '')}")
    print(f"标签: {meta.get('tags', '')}")
    print(f"创建时间: {meta.get('created_at', '')}")
    print(f"更新时间: {meta.get('updated_at', '')}")
    print(f"路径: {meta.get('path', '')}")
    print()
    print("=" * 60)
    print("代码内容:")
    print("=" * 60)
    print(content)


def _read_tool_content(args) -> str:
    """从 --file 或 --stdin 读取工具代码。"""
    if args.file:
        file_path = resolve_file_path(args.file)
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    if args.stdin:
        return sys.stdin.read()
    print("错误: 必须指定 --file 或 --stdin", file=sys.stderr)
    sys.exit(1)


def _read_publish_content(args) -> str:
    """读取 publish 要上传的工具代码。"""
    validate_tool_identity(args.project, args.name)
    if args.file or args.stdin:
        return _read_tool_content(args)

    project_root = resolve_project_root()
    local_path = project_root / "tools" / args.project / f"{args.name}.py"
    if not local_path.is_file():
        print(
            f"错误: 本地工具文件不存在: {local_path}；请指定 --file 或 --stdin",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(local_path, "r", encoding="utf-8") as f:
        return f.read()


def _generate_local_tool_template(args) -> str:
    """生成本地 create 使用的最小 NiceTool 模板。"""
    today = datetime.now().strftime("%Y-%m-%d")
    title = args.title or args.name.replace("_", " ").replace("-", " ").title()
    description = args.description or f"{title} tool"
    creator = args.creator or "tool-cli"
    tags = args.tags or "local,draft"
    return f'''"""
project: {args.project}
name: {args.name}
description: {description}
creator: {creator}
created_at: {today}
updated_at: {today}
tags: {tags}
"""

from nicegui import ui


def main():
    ui.label("{title}").classes("text-lg font-medium")


if __name__ in {{"__main__", "__mp_main__"}}:
    main()
    ui.run(title="{title}", port=8080, show=True)
'''


def cmd_create(args):
    """本地创建工具文件，不调用服务端 create。"""
    validate_tool_identity(args.project, args.name)
    content = (
        _read_tool_content(args)
        if args.file or args.stdin
        else _generate_local_tool_template(args)
    )
    project_root = resolve_project_root()
    output_path = project_root / "tools" / args.project / f"{args.name}.py"

    if output_path.exists():
        message = f"工具已存在: {output_path}"
        if args.json:
            print(
                json.dumps(
                    {"success": False, "error": message, "path": str(output_path)},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"✗ {message}", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    result = {
        "success": True,
        "project": args.project,
        "name": args.name,
        "path": str(output_path),
        "message": "已本地创建工具文件；未调用服务端 create，未发布正式版本",
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"✓ 本地创建成功: {args.project}/{args.name}")
    print(f"  路径: {output_path}")
    print("  未调用服务端 create，未发布正式版本")


def cmd_publish(args):
    """上传工具内容并发布。"""
    _confirm_production_write(args, "publish")
    content = _read_publish_content(args)
    url = f"{args.server}/api/tools/{args.project}/{args.name}/publish"
    result = make_request(url, method="POST", data={"content": content})

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if result.get("success"):
        public_url = build_public_url(
            args.server,
            result.get("url") or f"/user/tools/{args.project}/{args.name}",
        )
        print(f"✓ 发布成功: {args.project}/{args.name}")
        print(f"  正式地址: {public_url}")
    else:
        print(
            f"✗ 发布失败: {result.get('message') or result.get('error') or '未知错误'}"
        )
        sys.exit(1)


def cmd_status(args):
    """查看工具正式状态。"""
    url = f"{args.server}/api/tools/{args.project}/{args.name}/state"
    result = make_request(url)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if not result.get("success", False):
        print(
            f"✗ 状态查询失败: {result.get('message') or result.get('error') or '未知错误'}"
        )
        sys.exit(1)

    tool = result.get("tool", {})
    state = result.get("state", {})
    formal_url = build_public_url(
        args.server,
        tool.get("url") or f"/user/tools/{args.project}/{args.name}",
    )
    print(f"✓ 工具状态: {args.project}/{args.name}")
    print(f"  正式地址: {formal_url}")
    print(f"  当前版本: {tool.get('current_version') or '未发布'}")
    print(f"  已发布: {'是' if state.get('published') else '否'}")
    print(f"  更新时间: {tool.get('updated_at') or '-'}")


def cmd_delete(args):
    """删除工具"""
    _confirm_production_write(args, "delete")
    if not getattr(args, "production", False) and not args.yes:
        confirm = input(f"确定要删除 {args.project}/{args.name}? [y/N] ")
        if confirm.lower() != "y":
            print("已取消")
            return

    url = f"{args.server}/api/tools/{args.project}/{args.name}"
    result = make_request(url, method="DELETE")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if result.get("success"):
        print(f"✓ 删除成功: {args.project}/{args.name}")
    else:
        print(f"✗ 删除失败: {result.get('error', '未知错误')}")
        sys.exit(1)


def _confirm_production_write(args, action: str) -> None:
    if not getattr(args, "production", False):
        return
    if getattr(args, "yes", False):
        if not getattr(args, "json", False):
            _print_write_target(args, action)
        return
    if getattr(args, "json", False) or not sys.stdin.isatty():
        raise ApiError(
            400,
            {
                "success": False,
                "code": "production_confirmation_required",
                "message": "拒绝非交互式生产操作，请显式传入 --yes",
                "next_action": "confirm_production_action",
            },
            "拒绝非交互式生产操作，请显式传入 --yes",
        )
    _print_write_target(args, action)
    confirm = input("确认继续? [y/N] ")
    if confirm.lower() != "y":
        print("已取消")
        raise SystemExit(0)


def _print_write_target(args, action: str) -> None:
    print(f"环境: {getattr(args, 'environment', None) or 'custom'}")
    print(f"服务: {args.server}")
    print(f"工具: {args.project}/{args.name}")
    print(f"动作: {action}")


def cmd_preview(args):
    """预览工具"""
    if bool(args.project) != bool(args.name):
        raise ApiError(
            400,
            {
                "success": False,
                "code": "invalid_arguments",
                "message": "固定预览必须同时提供 project 和 name",
                "next_action": "provide_project_and_name",
            },
            "固定预览必须同时提供 project 和 name",
        )

    content = _read_tool_content(args)

    if args.project and args.name:
        url = f"{args.server}/api/tools/preview/{args.project}/{args.name}"
    else:
        url = f"{args.server}/api/tools/preview"
    data = {"content": content}

    result = make_request(url, method="POST", data=data)
    result["preview_url"] = build_public_url(
        args.server,
        result.get("preview_url") or result.get("url", ""),
    )
    if result.get("log_url"):
        result["log_url"] = build_public_url(args.server, result["log_url"])

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"✓ 预览地址: {result['preview_url']}")
    if result.get("log_url"):
        print(f"  日志地址: {result['log_url']}")
    if result.get("key"):
        print(f"  preview_key: {result['key']}")
    print(f"  {result.get('message', '')}")


def cmd_databases(args):
    """列出数据源"""
    url = f"{args.server}/api/datasources"
    if args.type:
        url += f"?type={args.type}"

    result = make_request(url)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    datasources = result.get("datasources", [])
    print(f"共 {result.get('total', len(datasources))} 个数据源\n")

    if datasources:
        headers = ["名称", "类型", "主机", "端口", "数据库", "状态", "描述"]
        rows = [
            [
                ds.get("name", ""),
                ds.get("type", "").upper(),
                ds.get("host", ""),
                str(ds.get("port", "")),
                ds.get("database", ""),
                "启用" if ds.get("is_active") else "禁用",
                (ds.get("description") or "")[:30],
            ]
            for ds in datasources
        ]
        print_table(headers, rows)


def cmd_variables(args):
    """列出可用平台变量 Key，不读取 Value。"""
    url = f"{args.server}/api/variables"
    if args.search:
        url += f"?{urlencode({'search': args.search})}"

    result = make_request(url)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    items = result.get("variables", [])
    print(f"共 {result.get('total', len(items))} 个变量\n")
    print_table(
        ["Key", "备注"],
        [[item.get("key", ""), item.get("remark", "")] for item in items],
    )


def cmd_toollog(args):
    """查看工具日志"""
    import subprocess

    # 工具日志目录: <project_root>/logs/tools/{project}/{tool_name}/tool.log
    log_base = resolve_project_root() / "logs" / "tools"

    if args.project and args.name:
        # 查看指定工具的日志
        log_file = log_base / args.project / args.name / "tool.log"
        if not log_file.is_file():
            print(f"✗ 日志文件不存在: {log_file}")
            sys.exit(1)

        lines = args.lines or 50
        if args.follow:
            print(f"📋 实时跟踪日志: {args.project}/{args.name}")
            print(f"   文件: {log_file}")
            print("=" * 60)
            subprocess.run(["tail", "-f", "-n", str(lines), str(log_file)], check=False)
        elif args.grep:
            print(f"🔍 搜索日志: {args.project}/{args.name} (关键词: {args.grep})")
            print("=" * 60)
            subprocess.run(
                ["grep", "--color=auto", "-n", args.grep, str(log_file)], check=False
            )
        else:
            print(f"📋 工具日志: {args.project}/{args.name} (最近 {lines} 行)")
            print(f"   文件: {log_file}")
            print("=" * 60)
            subprocess.run(["tail", "-n", str(lines), str(log_file)], check=False)
    else:
        # 列出所有有日志的工具
        if not log_base.is_dir():
            print("(暂无工具日志)")
            return

        headers = ["项目", "名称", "日志大小", "最后修改"]
        rows = []
        for project_name in sorted(p.name for p in log_base.iterdir() if p.is_dir()):
            project_dir = log_base / project_name
            for tool_name in sorted(
                p.name for p in project_dir.iterdir() if p.is_dir()
            ):
                log_file = project_dir / tool_name / "tool.log"
                if log_file.is_file():
                    stat = log_file.stat()
                    from datetime import datetime

                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    size = _format_size(stat.st_size)
                    rows.append([project_name, tool_name, size, mtime])

        if rows:
            print(f"共 {len(rows)} 个工具有日志\n")
            print_table(headers, rows)
            print("\n💡 查看日志: python scripts/tool-cli.py toollog <project> <name>")
            print("💡 实时跟踪: python scripts/tool-cli.py toollog <project> <name> -f")
        else:
            print("(暂无工具日志)")


def cmd_prelog(args):
    """查看预览工具日志（通过服务端 API，不直接访问文件系统）"""
    if getattr(args, "json", False):
        from preview_log import snapshot

        result = snapshot(args, make_request, make_raw_request)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        if not result["success"]:
            sys.exit(1)
        return
    server = args.server

    if args.name and not args.target:
        raise ApiError(
            400,
            {
                "success": False,
                "code": "invalid_arguments",
                "message": "固定预览日志必须同时提供 project 和 name",
                "next_action": "provide_project_and_name",
            },
            "固定预览日志必须同时提供 project 和 name",
        )

    if args.target:
        token = args.target
        lines = args.lines or 50
        is_fixed = bool(args.name)
        if is_fixed:
            log_url = f"{server}/api/tools/preview/log/fixed/{args.target}/{args.name}"
            label = f"{args.target}/{args.name}"
        else:
            log_url = f"{server}/api/tools/preview/log/{token}"
            label = token[:16] + "..."

        status, log_content = make_raw_request(f"{log_url}?lines={lines}")
        if status == 404:
            print(f"✗ 预览日志不存在: {label}")
            sys.exit(1)
        if status != 200:
            print(f"✗ 获取日志失败: HTTP {status}\n{log_content}")
            sys.exit(1)

        if args.grep:
            print(f"🔍 搜索预览日志: {label} (关键词: {args.grep})")
            print("=" * 60)
            for i, line in enumerate(log_content.splitlines(), 1):
                if args.grep.lower() in line.lower():
                    print(f"{i}: {line}")
        elif args.follow:
            import time

            print(f"📋 实时跟踪预览日志: {label}")
            print("=" * 60)
            print(log_content, end="")
            seen_lines = len(log_content.splitlines())
            try:
                while True:
                    time.sleep(1)
                    s, text = make_raw_request(f"{log_url}?lines=1000")
                    if s == 200:
                        new_lines = text.splitlines()
                        if len(new_lines) > seen_lines:
                            for line in new_lines[seen_lines:]:
                                print(line)
                            seen_lines = len(new_lines)
            except KeyboardInterrupt:
                pass
        else:
            print(f"📋 预览日志: {label} (最近 {lines} 行)")
            print("=" * 60)
            print(log_content)
    else:
        # 列出所有预览工具
        result = make_request(f"{server}/api/tools/preview/list")
        tools = result.get("tools", [])
        if not tools:
            print("(暂无预览工具)")
            return

        headers = ["Token", "名称", "日志大小", "最后修改"]
        rows = []
        for t in tools:
            token = t["token"]
            log_size = _format_size(t["log_size"]) if t["has_log"] else "(无日志)"
            rows.append(
                [token[:16] + "...", t.get("title") or "-", log_size, t["created_at"]]
            )

        print(f"共 {len(rows)} 个预览工具\n")
        print_table(headers, rows)
        print("\n💡 查看日志: python scripts/tool-cli.py prelog <token>")
        print("💡 固定预览日志: python scripts/tool-cli.py prelog <project> <name>")
        print("💡 实时跟踪: python scripts/tool-cli.py prelog <token> -f")


def _format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def main():
    parser = argparse.ArgumentParser(
        description="Tool CLI - 工具管理命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--server",
        default=None,
        help="临时覆盖环境的服务器地址",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="访问令牌 (默认: 环境变量 NICETOOL_TOKEN)",
    )
    parser.add_argument("--env", dest="environment", help="命名环境")
    parser.add_argument("--config", help="NiceTool TOML 配置文件路径")
    parser.add_argument(
        "--skill-root",
        action="store_true",
        help="打印本 skill 根目录路径后退出（调试用）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出工具")
    list_parser.add_argument("--project", "-p", help="按项目过滤")
    list_parser.set_defaults(func=cmd_list)

    # projects 命令
    projects_parser = subparsers.add_parser("projects", help="列出工具项目")
    projects_parser.set_defaults(func=cmd_projects)

    # get 命令
    get_parser = subparsers.add_parser("get", help="获取工具详情")
    get_parser.add_argument("project", help="所属项目")
    get_parser.add_argument("name", help="工具名称")
    get_parser.add_argument("--output", "-o", help="写入本地文件")
    get_parser.set_defaults(func=cmd_get)

    # create 命令
    create_parser = subparsers.add_parser(
        "create", help="本地创建工具文件，不调用服务端 create"
    )
    create_parser.add_argument("project", help="所属项目")
    create_parser.add_argument("name", help="工具名称")
    create_parser.add_argument("--file", "-f", help="从文件读取代码")
    create_parser.add_argument(
        "--stdin", action="store_true", help="从标准输入读取代码"
    )
    create_parser.add_argument("--title", help="工具标题")
    create_parser.add_argument("--description", help="工具描述")
    create_parser.add_argument("--creator", help="创建者")
    create_parser.add_argument("--tags", help="工具标签，逗号分隔，如 data,export")
    create_parser.set_defaults(func=cmd_create)

    # publish 命令
    publish_parser = subparsers.add_parser("publish", help="上传工具内容并发布")
    publish_parser.add_argument("project", help="所属项目")
    publish_parser.add_argument("name", help="工具名称")
    publish_parser.add_argument("--file", "-f", help="从文件读取代码")
    publish_parser.add_argument(
        "--stdin", action="store_true", help="从标准输入读取代码"
    )
    publish_parser.add_argument("--yes", "-y", action="store_true", help="确认生产发布")
    publish_parser.set_defaults(func=cmd_publish)

    # status 命令
    status_parser = subparsers.add_parser("status", help="查看工具正式状态")
    status_parser.add_argument("project", help="所属项目")
    status_parser.add_argument("name", help="工具名称")
    status_parser.set_defaults(func=cmd_status)

    # delete 命令
    delete_parser = subparsers.add_parser("delete", help="删除工具")
    delete_parser.add_argument("project", help="所属项目")
    delete_parser.add_argument("name", help="工具名称")
    delete_parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    delete_parser.set_defaults(func=cmd_delete)

    # preview 命令
    preview_parser = subparsers.add_parser("preview", help="预览工具")
    preview_parser.add_argument("project", nargs="?", help="固定预览所属项目")
    preview_parser.add_argument("name", nargs="?", help="固定预览工具名称")
    preview_parser.add_argument("--file", "-f", help="从文件读取代码")
    preview_parser.add_argument(
        "--stdin", action="store_true", help="从标准输入读取代码"
    )
    preview_parser.set_defaults(func=cmd_preview)

    # databases 命令
    databases_parser = subparsers.add_parser("databases", help="列出数据源")
    databases_parser.add_argument("--type", "-t", help="按类型过滤: mysql/mongodb")
    databases_parser.set_defaults(func=cmd_databases)

    # variables 命令
    variables_parser = subparsers.add_parser(
        "variables", help="列出平台变量 Key（不返回 Value）"
    )
    variables_parser.add_argument("--search", "-s", help="按 Key 或备注搜索")
    variables_parser.set_defaults(func=cmd_variables)

    # toollog 命令
    toollog_parser = subparsers.add_parser("toollog", help="查看工具日志")
    toollog_parser.add_argument("project", nargs="?", help="所属项目")
    toollog_parser.add_argument("name", nargs="?", help="工具名称")
    toollog_parser.add_argument(
        "--follow", "-f", action="store_true", help="实时跟踪日志 (tail -f)"
    )
    toollog_parser.add_argument("--lines", "-n", type=int, help="显示行数 (默认 50)")
    toollog_parser.add_argument("--grep", "-g", help="搜索关键词")
    toollog_parser.set_defaults(func=cmd_toollog)

    # prelog 命令
    prelog_parser = subparsers.add_parser("prelog", help="查看预览工具日志")
    prelog_parser.add_argument(
        "target", nargs="?", help="预览工具 token，或固定预览 project"
    )
    prelog_parser.add_argument("name", nargs="?", help="固定预览工具名称")
    prelog_parser.add_argument(
        "--follow", "-f", action="store_true", help="实时跟踪日志 (tail -f)"
    )
    prelog_parser.add_argument("--lines", "-n", type=int, help="显示行数 (默认 50)")
    prelog_parser.add_argument("--grep", "-g", help="搜索关键词")
    prelog_parser.add_argument(
        "--max-chars",
        type=int,
        default=8000,
        help="JSON 日志保留末尾字符数（默认 8000，仅用于 --json）",
    )
    prelog_parser.set_defaults(func=cmd_prelog)

    args = parser.parse_args()

    if getattr(args, "skill_root", False):
        print(SKILL_ROOT)
        sys.exit(0)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command in {"create", "get", "publish", "status", "delete", "list"}:
        project = getattr(args, "project", None)
        if project is not None:
            try:
                validate_tool_identity(project, getattr(args, "name", "check"))
            except ValueError as error:
                parser.error(str(error))

    if args.command == "create":
        args.func(args)
        return

    try:
        runtime = resolve_runtime(
            explicit_environment=args.environment,
            explicit_config=args.config,
            explicit_server=args.server,
            explicit_token=args.token,
        )
    except ConfigError as error:
        parser.error(str(error))
    args.server = runtime["server"]
    args.environment = runtime["environment"]
    args.production = runtime["production"]
    make_request.token = runtime["token"]

    try:
        args.func(args)
    except ApiError as e:
        if args.json:
            print(json.dumps(e.data, ensure_ascii=False, indent=2))
        else:
            print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        if args.json:
            print(
                json.dumps(
                    normalize_error_payload({"error": str(e)}),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
