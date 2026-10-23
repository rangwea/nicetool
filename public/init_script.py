"""NiceTool 客户端配置初始化脚本。"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from core.settings import settings
from service import nicetool_environment_service

router = APIRouter(tags=["nicetool-bootstrap"])


def _external_base_url(request: Request, config: dict) -> str:
    """优先使用与当前主机匹配的已登记外部环境地址。"""
    return nicetool_environment_service.resolve_external_base_url(
        str(request.base_url), settings.get_project_path(), config
    )


@router.get("/api/init.sh", response_class=PlainTextResponse)
def nicetool_init_script() -> PlainTextResponse:
    """返回不含 Token 值的独立 NiceTool 配置初始化脚本。"""
    try:
        script = nicetool_environment_service.render_init_script()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PlainTextResponse(
        script,
        media_type="text/x-shellscript; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/api/install.sh", response_class=PlainTextResponse)
def nicetool_install_script(request: Request) -> PlainTextResponse:
    """返回安装 Skill、初始化环境并提示自助生成 Token 的脚本。"""
    try:
        config = nicetool_environment_service.build_client_config()
        base_url = _external_base_url(request, config)
        script = nicetool_environment_service.render_install_script(
            download_url=base_url + "/api/downloads/nicetool-skill.zip",
            init_url=base_url + "/api/init.sh",
            config=config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PlainTextResponse(
        script,
        media_type="text/x-shellscript; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )
