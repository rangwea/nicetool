"""
统一异常处理模块
提供装饰器和工具函数来统一处理异常并通过 ui.notify 显示错误信息
"""

import functools
from collections.abc import Callable
from typing import Any

from nicegui import ui

from core.logger import get_logger

logger = get_logger(__name__)


def handle_service_errors(
    default_message: str = "操作失败",
    show_notification: bool = True,
    return_on_error: Any = None,
):
    """
    统一异常处理装饰器，用于 public 层函数

    Args:
        default_message: 默认错误消息
        show_notification: 是否显示通知
        return_on_error: 发生错误时的返回值
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e) if str(e) else default_message
                logger.error(f"Error in {func.__name__}: {error_msg}", exc_info=True)  # noqa: G201 — 保留现有日志级别和上下文字段。
                if show_notification:
                    ui.notify(error_msg, type="negative")
                return return_on_error

        return wrapper

    return decorator
