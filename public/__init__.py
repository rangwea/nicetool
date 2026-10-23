"""
NiceTool 公共模块
按功能分为 admin、user、client 和 agent 四个包
"""

# 页面导入会注册路由，保留既有注册顺序。
# ruff: noqa: I001
# 导入管理员功能
from .admin import admin_index

# 导入用户功能
from .user import user_dashboard, tools_handler

# 导入客户端功能（临时/固定工具预览）
from .client import fixed_preview_handler, preview_handler

# 导入首页
from .index import index

__all__ = [
    # 管理员功能
    "admin_index",
    # 客户端功能
    "fixed_preview_handler",
    # 首页
    "index",
    "preview_handler",
    "tools_handler",
    # 用户功能
    "user_dashboard",
]
