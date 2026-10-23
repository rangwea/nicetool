"""
统一 Tool API

提供工具管理的 RESTful 接口：
- GET    /api/tools                    列出所有工具
- GET    /api/tools/projects           获取所有项目名称
- GET    /api/tools/preview/list       列出所有预览工具
- GET    /api/tools/preview/log/{key}  查看预览工具日志
- GET    /api/tools/{project}/{name}   获取工具详情
- POST   /api/tools/{project}/{name}/publish 发布工具
- DELETE /api/tools/{project}/{name}   删除工具
- POST   /api/tools/preview            临时预览工具
- POST   /api/tools/preview/{username}/{tool_name} 固定预览工具
"""

import os
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from core.auth.actor import TOOL_PREVIEW
from core.auth.dependencies import actor_from_request, current_user
from core.auth.service import auth_service
from core.tool_identity import InvalidToolIdentity, validate_project_name
from service import tool_lifecycle_service, tool_manage_service
from service.access_control_service import (
    allowed_projects,
    can_access_project,
    filter_tools_for_user,
)
from service.preview_service import (
    create_fixed_preview,
    fixed_preview_key_from_path,
    get_fixed_preview_log_url,
    get_preview_log_file,
    get_preview_log_url,
    list_previews,
    read_preview_code,
    validate_preview_key,
)

router = APIRouter(prefix="/api/tools", tags=["tools"])


# ============================================================================
# 请求/响应模型
# ============================================================================


class ToolContentRequest(BaseModel):
    """工具内容请求体"""

    content: str = Field(..., min_length=1, description="工具 Python 代码")


class ToolMetaResponse(BaseModel):
    """工具元数据响应"""

    project: str
    name: str
    title: str
    description: str
    creator: str
    created_at: str
    updated_at: str
    path: str
    tags: str = ""


class ListToolsResponse(BaseModel):
    """工具列表响应"""

    tools: list[ToolMetaResponse]
    total: int


class ToolProjectsResponse(BaseModel):
    """项目列表响应"""

    projects: list[str]


class ToolDetailResponse(BaseModel):
    """工具详情响应"""

    meta: ToolMetaResponse
    content: str | None = None


class PreviewResponse(BaseModel):
    """预览响应"""

    url: str
    message: str
    key: str | None = None
    preview_url: str | None = None
    log_url: str | None = None


def _lifecycle_failure_response(result):
    status_code = 400
    if result.code == "invalid_identity":
        status_code = 422
    elif result.code == "permission_denied":
        status_code = 403
    elif (
        result.code == "tool_not_found"
        or result.code == "delete_failed"
        and "不存在" in result.message
    ):
        status_code = 404
    return JSONResponse(status_code=status_code, content=result.to_dict())


def _require_project_access(request: Request, project: str) -> None:
    try:
        validate_project_name(project)
    except InvalidToolIdentity as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not can_access_project(current_user(request), project):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有该项目的访问权限",
        )


# ============================================================================
# API 路由
# ============================================================================


@router.get("", response_model=ListToolsResponse)
async def list_tools(
    request: Request,
    project: Annotated[str | None, Query(description="按项目过滤")] = None,
):
    """
    列出所有工具

    - **project**: 可选，按项目过滤
    """
    if project is not None:
        try:
            validate_project_name(project)
        except InvalidToolIdentity as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    user = current_user(request)
    if project and not can_access_project(user, project):
        tools = []
    else:
        tools = filter_tools_for_user(
            tool_manage_service.list_tools(project=project), user
        )
    return ListToolsResponse(tools=tools, total=len(tools))


@router.get("/projects", response_model=ToolProjectsResponse)
async def list_tool_projects(request: Request):
    """
    获取所有项目名称
    """
    projects = tool_manage_service.list_tool_projects()
    permitted = allowed_projects(current_user(request))
    if permitted is not None:
        projects = [project for project in projects if project in permitted]
    return ToolProjectsResponse(projects=projects)


@router.get("/preview/list")
async def list_preview_tools():
    """
    列出所有预览工具

    返回所有临时目录中的预览工具信息，包括 key、文件大小、日志状态等。
    """
    tools = list_previews()
    return {"tools": tools, "total": len(tools)}


@router.get("/preview/log/fixed/{username}/{tool_name}")
async def get_fixed_preview_log(
    username: str,
    tool_name: str,
    lines: Annotated[int, Query(ge=1, le=10000, description="返回最后N行")] = 100,
):
    preview_key = fixed_preview_key_from_path(username, tool_name)
    return await _get_preview_log_by_key(preview_key, lines)


@router.get("/preview/log/{preview_key}")
async def get_preview_log(
    preview_key: str,
    lines: Annotated[int, Query(ge=1, le=10000, description="返回最后N行")] = 100,
):
    """
    获取预览工具日志内容

    - **preview_key**: 预览工具 key
    - **lines**: 返回最后N行（默认100）
    """
    safe_key = validate_preview_key(preview_key)
    if safe_key is None:
        return PlainTextResponse(content="预览 key 不合法", status_code=400)
    return await _get_preview_log_by_key(safe_key, lines)


def _read_log_lines(log_file):
    with open(log_file, encoding="utf-8") as source:
        return source.readlines()


async def _get_preview_log_by_key(preview_key: str, lines: int):
    log_file = get_preview_log_file(preview_key)
    if not os.path.exists(log_file):
        return PlainTextResponse(
            content=f"日志文件不存在: {preview_key}",
            status_code=404,
        )

    try:
        all_lines = await run_in_threadpool(_read_log_lines, log_file)

        # 返回最后 N 行
        tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        content = "".join(tail_lines)
        return PlainTextResponse(content=content)
    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        return PlainTextResponse(
            content=f"读取日志失败: {e}",
            status_code=500,
        )


@router.get("/preview/code/fixed/{username}/{tool_name}")
async def get_fixed_preview_code(username: str, tool_name: str):
    preview_key = fixed_preview_key_from_path(username, tool_name)
    return await _get_preview_code_by_key(preview_key)


@router.get("/preview/code/{preview_key}")
async def get_preview_code(preview_key: str):
    """
    获取预览工具代码内容

    - **preview_key**: 预览工具 key
    """
    safe_key = validate_preview_key(preview_key)
    if safe_key is None:
        return PlainTextResponse(content="预览 key 不合法", status_code=400)
    return await _get_preview_code_by_key(safe_key)


async def _get_preview_code_by_key(preview_key: str):
    try:
        content = read_preview_code(preview_key)
    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        return PlainTextResponse(
            content=f"读取代码失败: {e}",
            status_code=500,
        )

    if content is None:
        return PlainTextResponse(
            content=f"预览工具不存在: {preview_key}",
            status_code=404,
        )

    return PlainTextResponse(content=content)


@router.post("/preview", response_model=PreviewResponse)
async def preview_tool(request: Request, body: ToolContentRequest):
    """
    临时预览工具

    上传代码后返回预览 URL，代码保存在临时目录，不会持久化。
    """
    actor = actor_from_request(request)
    result = tool_lifecycle_service.preview_tool(actor, body.content)
    if not result.success:
        return _lifecycle_failure_response(result)

    data = result.data

    return PreviewResponse(
        url=data["url"],
        message=result.message,
        key=data.get("key"),
        preview_url=data.get("preview_url") or data.get("url"),
        log_url=data.get("log_url")
        or (get_preview_log_url(data["key"]) if data.get("key") else None),
    )


@router.post("/preview/{username}/{tool_name}", response_model=PreviewResponse)
async def preview_fixed_tool(
    request: Request, username: str, tool_name: str, body: ToolContentRequest
):
    """
    固定预览工具

    同一个 username/tool_name 始终覆盖同一个预览文件，因此浏览器中的预览链接
    可以保持不变，编辑代码后刷新页面即可看到最新内容。
    """
    if not username.strip() or not tool_name.strip():
        return JSONResponse(
            status_code=400,
            content={"detail": "username 和 tool_name 不能为空"},
        )

    actor = actor_from_request(request)
    if not actor.has_scope(TOOL_PREVIEW):
        return _lifecycle_failure_response(
            tool_lifecycle_service.lifecycle_error(
                code="permission_denied",
                message=f"缺少权限: {TOOL_PREVIEW}",
                next_action="request_scope",
            )
        )

    # 认证关闭时保留原有行为；开启认证后按账号用户名确定所有权。
    if auth_service.is_enabled():
        user = current_user(request)
        if not user or (user.role != "admin" and username.strip() != user.username):
            raise HTTPException(status_code=403, detail="只能修改自己的固定预览")

    result = create_fixed_preview(username, tool_name, body.content)
    if not result["success"]:
        return JSONResponse(
            status_code=result["status_code"],
            content={
                "success": False,
                "code": result.get("code", "preview_failed"),
                "message": result.get("message") or result.get("error", "预览失败"),
                "next_action": result.get("next_action", "inspect_error"),
                **{
                    key: result[key]
                    for key in ("line", "column")
                    if result.get(key) is not None
                },
            },
        )

    return PreviewResponse(
        url=result["url"],
        message=result["message"],
        key=result["key"],
        preview_url=result.get("preview_url") or result["url"],
        log_url=get_fixed_preview_log_url(username, tool_name),
    )


@router.get("/{project}/{name}", response_model=ToolDetailResponse)
async def get_tool(
    request: Request,
    project: str,
    name: str,
    content: Annotated[bool, Query(description="是否包含代码内容")] = False,
):
    """
    获取工具详情

    - **project**: 所属项目
    - **name**: 工具名称
    - **content**: 是否包含代码内容
    """
    _require_project_access(request, project)
    try:
        result = tool_manage_service.get_tool(project, name, include_content=content)
    except InvalidToolIdentity as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if result is None:
        return JSONResponse(
            status_code=404,
            content={"detail": f"工具不存在: {project}/{name}"},
        )

    return ToolDetailResponse(
        meta=result["meta"],
        content=result.get("content"),
    )


@router.get("/{project}/{name}/state")
async def get_tool_state(request: Request, project: str, name: str):
    """
    获取工具正式状态

    - **project**: 所属项目
    - **name**: 工具名称
    """
    _require_project_access(request, project)
    actor = actor_from_request(request)
    result = tool_lifecycle_service.get_tool_state(actor, project, name)
    if not result.success:
        return _lifecycle_failure_response(result)
    return result.to_dict()


@router.post("/{project}/{name}/publish")
async def publish_tool(
    request: Request,
    project: str,
    name: str,
    body: ToolContentRequest,
):
    """
    发布工具

    - **project**: 所属项目
    - **name**: 工具名称
    - **content**: 必填；使用上传源码创建正式版本
    """
    _require_project_access(request, project)
    actor = actor_from_request(request)
    result = tool_lifecycle_service.publish_tool(
        actor,
        project,
        name,
        content=body.content,
    )
    if not result.success:
        return _lifecycle_failure_response(result)
    return result.to_dict()


@router.delete("/{project}/{name}")
async def delete_tool(request: Request, project: str, name: str):
    """
    删除工具

    - **project**: 所属项目
    - **name**: 工具名称
    """
    _require_project_access(request, project)
    actor = actor_from_request(request)
    result = tool_lifecycle_service.delete_tool(actor, project, name)
    if not result.success:
        return _lifecycle_failure_response(result)

    return {"success": True}
