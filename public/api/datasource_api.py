"""
数据源 API

提供数据源查询接口：
- GET /api/datasources           列出所有数据源
- GET /api/datasources/{name}    获取数据源详情
- POST /api/datasources/{name}/test  测试数据源连接
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from core.logger import get_logger
from service import datasource_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/datasources", tags=["datasources"])


@router.get("")
async def list_datasources(
    type: str | None = Query(None, description="按类型过滤: mysql/mongodb"),
    is_active: bool | None = Query(None, description="按状态过滤"),
):
    """列出所有数据源"""
    datasources = datasource_service.list_datasources(
        ds_type=type,
        is_active=is_active,
    )

    # 隐藏密码
    result = []
    for ds in datasources:
        item = ds.model_dump()
        item["password"] = "******"
        result.append(item)

    return {"datasources": result, "total": len(result)}


@router.get("/{name}")
async def get_datasource(name: str):
    """获取数据源详情"""
    ds = datasource_service.get_datasource_by_name(name)
    if ds is None:
        return JSONResponse(
            status_code=404,
            content={"detail": f"数据源不存在: {name}"},
        )

    item = ds.model_dump()
    item["password"] = "******"
    return item


@router.post("/{name}/test")
async def test_datasource(name: str):
    """测试数据源连接"""
    from core.datasource_manager import datasource_manager

    if datasource_manager is None:
        return {"success": False, "message": "数据源管理器未初始化"}

    success = datasource_manager.test_datasource(name)
    return {
        "success": success,
        "message": "连接成功" if success else "连接失败",
    }
