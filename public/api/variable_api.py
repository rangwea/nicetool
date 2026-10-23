"""工具变量只读发现 API。"""

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from service import variable_service

router = APIRouter(prefix="/api/variables", tags=["variables"])


class VariableKeyResponse(BaseModel):
    """不包含变量值的发现信息。"""

    key: str
    remark: str


class VariableKeyListResponse(BaseModel):
    """变量 Key 列表响应。"""

    variables: list[VariableKeyResponse]
    total: int


@router.get("", response_model=VariableKeyListResponse)
def list_variable_keys(
    search: Annotated[str | None, Query(description="按 Key 或备注搜索")] = None,
) -> VariableKeyListResponse:
    """列出工具可引用的变量 Key 和备注，绝不返回 Value。"""
    variables = variable_service.list_variable_keys(search)
    return VariableKeyListResponse(variables=variables, total=len(variables))
