"""
NiceTool 主应用
提供工具管理和Web界面
"""

import datetime

# 扩展 NiceGUI 的 orjson 序列化器，支持 pandas.Timestamp 等非标准类型
import nicegui.json.orjson_wrapper as _orjson_mod
import uvicorn
from fastapi import FastAPI
from nicegui import ui
from starlette.middleware.sessions import SessionMiddleware

_original_converter = _orjson_mod._orjson_converter


def _extended_orjson_converter(obj):
    """扩展的 orjson 类型转换器，支持 pandas.Timestamp、datetime 等类型"""
    # pandas.Timestamp
    if hasattr(obj, "isoformat") and callable(obj.isoformat):
        return obj.isoformat()
    # datetime.date / datetime.time
    if isinstance(obj, (datetime.date, datetime.time)):
        return obj.isoformat()
    return _original_converter(obj)


_orjson_mod._orjson_converter = _extended_orjson_converter

# 导入页面模块以注册路由
import public  # noqa: F401
from core.auth.middleware import AuthMiddleware
from core.database import db_manager
from core.datasource_manager import datasource_manager
from core.logger import get_logger
from core.settings import settings
from core.styles import apply_app_styles
from public.api.auth_api import api_router as device_auth_api_router
from public.api.auth_api import router as auth_api_router
from public.api.datasource_api import router as datasource_api_router
from public.api.health_api import router as health_api_router

# 导入 FastAPI 路由
from public.api.tool_api import router as tool_api_router
from public.api.variable_api import router as variable_api_router
from public.init_script import router as init_script_router
from public.skill_download import router as skill_download_router

logger = get_logger(__name__)


if __name__ in {"__main__", "__mp_main__"}:
    try:
        env_config = settings.get_env_config_selection()
        logger.info(
            "加载环境配置: "
            f"ENV_TYPE={env_config.env_type}, "
            f"source={env_config.source}, "
            f"env_files={','.join(env_config.env_files)}"
        )

        # 初始化数据库表
        if db_manager:
            logger.info("创建数据库表")
            db_manager.create_tables()
            from service.tool_storage import (
                restore_all_current_tools,
            )

            restore_result = restore_all_current_tools()
            if restore_result.get("success"):
                logger.info(
                    f"工具运行缓存恢复完成: {restore_result.get('restored', 0)} 个"
                )
            else:
                logger.warning(f"工具运行缓存恢复存在异常: {restore_result}")

        # 创建FastAPI应用
        project_path = settings.get_project_path()
        fapp = FastAPI(
            title="小工具管理平台",
            description="基于NiceGUI的工具管理平台",
            version="1.0.0",
            docs_url=settings.path_for("/docs"),
            redoc_url=settings.path_for("/redoc"),
            openapi_url=settings.path_for("/openapi.json"),
        )

        fapp.add_middleware(AuthMiddleware)
        fapp.add_middleware(
            SessionMiddleware,
            secret_key=settings.storage_secret,
            session_cookie=settings.auth_flow_cookie_name,
            max_age=600,
            https_only=settings.auth_require_https_cookie,
            same_site="lax",
        )

        # 注册 FastAPI 路由
        fapp.include_router(health_api_router, prefix=project_path)
        fapp.include_router(auth_api_router, prefix=project_path)
        fapp.include_router(device_auth_api_router, prefix=project_path)
        fapp.include_router(tool_api_router, prefix=project_path)
        fapp.include_router(datasource_api_router, prefix=project_path)
        fapp.include_router(variable_api_router, prefix=project_path)
        fapp.include_router(init_script_router, prefix=project_path)
        fapp.include_router(skill_download_router, prefix=project_path)

        # 设置NiceGUI应用主题
        apply_app_styles()

        # 将NiceGUI挂载到FastAPI
        nicegui_config = settings.get_nicegui_config()
        ui.run_with(
            fapp,
            storage_secret=settings.storage_secret,
            language=nicegui_config.get("language", "zh-CN"),
            mount_path=nicegui_config.get("mount_path") or "/",
        )

        logger.info("应用设置完成")

        # 获取配置
        host = settings.host
        port = settings.port

        logger.info(f"启动应用服务器 http://{host}:{port}{settings.path_for()}")

        # 使用uvicorn启动FastAPI应用
        uvicorn.run(
            fapp,
            host=host,
            port=port,
            log_config=None,  # 禁用uvicorn默认日志配置，使用我们的日志配置
            access_log=False,  # 禁用默认访问日志，使用我们的中间件
        )

    except Exception as e:
        logger.error(f"启动应用失败: {e!s}")
        raise
    finally:
        # 清理资源
        if db_manager:
            db_manager.close()
        if datasource_manager:
            datasource_manager.close_all()
        logger.info("应用已关闭")
