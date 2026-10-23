"""健康检查 API。"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_class=PlainTextResponse)
async def health():
    """健康检查。"""
    return "OK"
