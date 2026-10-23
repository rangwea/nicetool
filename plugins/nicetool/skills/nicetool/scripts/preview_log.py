"""Bounded JSON snapshots for the Python 3 CLI client."""


def snapshot(args, request, raw_request):
    """Read once; never poll, execute code, or make a write request."""
    lines = args.lines if args.lines is not None else 50
    max_chars = getattr(args, "max_chars", 8000)
    if args.follow or not 1 <= lines <= 10000 or max_chars < 1:
        return {
            "success": False,
            "code": "invalid_arguments",
            "message": "JSON 日志需单次读取：禁用 --follow，lines 为 1–10000，max-chars 为正数",
            "next_action": "correct_arguments",
        }
    if args.name and not args.target:
        return {
            "success": False,
            "code": "invalid_arguments",
            "message": "固定预览日志必须同时提供 project 和 name",
            "next_action": "provide_project_and_name",
        }
    if not args.target:
        result = request(args.server + "/api/tools/preview/list")
        return {"success": True, "tools": result.get("tools", [])}

    if args.name:
        url = f"{args.server}/api/tools/preview/log/fixed/{args.target}/{args.name}"
    else:
        url = f"{args.server}/api/tools/preview/log/{args.target}"
    status, content = raw_request(url + "?lines=" + str(lines))
    if status != 200:
        # 不把 HTML 错误页或可能含配置值的网络异常灌入模型上下文。
        return {
            "success": False,
            "code": "preview_log_unavailable",
            "status": status,
            "message": "无法读取预览日志",
            "next_action": "check_access"
            if status in (401, 403)
            else "check_preview_or_connection",
        }
    content = "".join(content.splitlines(True)[-lines:])
    if args.grep:
        content = "".join(
            line
            for line in content.splitlines(True)
            if args.grep.lower() in line.lower()
        )
    return {
        "success": True,
        "log_url": url,
        "requested_lines": lines,
        "truncated": len(content) > max_chars,
        "content": content[-max_chars:],
    }
