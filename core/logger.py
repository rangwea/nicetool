import logging
import logging.handlers
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from loguru import logger

# ── 上下文变量：标记当前的执行环境 ────────────────────────────────────────────────
_current_preview_token: ContextVar[str | None] = ContextVar(
    "_current_preview_token", default=None
)
_current_tool_type: ContextVar[str | None] = ContextVar(
    "_current_tool_type", default=None
)
_current_tool_name: ContextVar[str | None] = ContextVar(
    "_current_tool_name", default=None
)

# ── 日志目录常量 ────────────────────────────────────────────────────────────────
LOG_BASE_DIR = Path("logs")
"""admin 项目日志根目录"""

LOG_TOOLS_DIR = LOG_BASE_DIR / "tools"
"""tool 日志按名称分目录: logs/tools/{tool_type}/{tool_name}/"""

_TMP_DIR = Path("/tmp/nicegui_client_tools")
"""预览临时文件目录: /tmp/nicegui_client_tools/{token}.py"""

_PREVIEW_LOG_DIR = _TMP_DIR / "_logs"
"""预览临时日志目录: /tmp/nicegui_client_tools/_logs/{token}.log"""

# ── 日志格式 ────────────────────────────────────────────────────────────────────
_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)
_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)
_PREVIEW_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {function}:{line} - {message}"
"""预览日志格式：不含模块名，更简洁"""


class InterceptHandler(logging.Handler):
    """拦截标准库 logging 的处理器，将日志转发给 loguru

    转发时自动附带 ContextVar 中的 preview_token / tool_type / tool_name，
    确保用户代码中通过标准 logging 产生的日志也能写入正确的 sink。
    """

    def emit(self, record):
        # 获取对应的 loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 找到调用者的帧
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # 读取当前上下文变量并 bind 到 loguru
        extra = {}
        token = _current_preview_token.get()
        if token:
            extra["preview_token"] = token
        tool_type = _current_tool_type.get()
        tool_name = _current_tool_name.get()
        if tool_type and tool_name:
            extra["tool_type"] = tool_type
            extra["tool_name"] = tool_name

        bound_logger = logger.bind(**extra) if extra else logger
        bound_logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logger():
    """配置日志系统

    日志存储策略：
    1. admin 项目日志 → logs/app.log + logs/error.log
    2. tool 日志通过 get_tool_logger() 按 tool_type/tool_name 分目录
    3. 预览临时日志通过 get_preview_logger() 存入临时目录
    """
    # 移除默认处理器
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stdout,
        format=_CONSOLE_FORMAT,
        level="INFO",
        colorize=True,
    )

    # 创建日志目录
    LOG_BASE_DIR.mkdir(exist_ok=True)

    # 文件输出 - 所有日志（admin 项目）
    logger.add(
        LOG_BASE_DIR / "app.log",
        format=_FILE_FORMAT,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    # 文件输出 - 错误日志（admin 项目）
    logger.add(
        LOG_BASE_DIR / "error.log",
        format=_FILE_FORMAT,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    return logger


def setup_third_party_logging():
    """配置第三方库日志拦截"""
    # 拦截标准库 logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


# ── 初始化 ──────────────────────────────────────────────────────────────────────
app_logger = setup_logger()
setup_third_party_logging()


# ── 公开 API ────────────────────────────────────────────────────────────────────


def get_logger(name: str = ""):
    """获取指定名称的日志器（admin 通用）"""
    if name:
        return logger.bind(name=name)
    return logger


def get_tool_logger(tool_type: str, tool_name: str):
    """获取 tool 专属日志器，日志写入 logs/tools/{tool_type}/{tool_name}/tool.log

    Args:
        tool_type: 工具类型（目录名），如 'demo'
        tool_name: 工具名称（文件名，不含 .py），如 'hello'

    Returns:
        绑定了 tool 上下文的 loguru logger 实例
    """
    tool_log_dir = LOG_TOOLS_DIR / tool_type / tool_name
    tool_log_dir.mkdir(parents=True, exist_ok=True)

    log_file = tool_log_dir / "tool.log"

    # 使用 filter 确保只有该 tool 的日志写入对应文件
    # loguru 的 add 是幂等的（不同 sink path 不会重复添加同一个文件）
    # 但为避免重复 add，用一个 set 记录已注册的路径
    _register_tool_sink(str(log_file), tool_type, tool_name)

    return logger.bind(
        name=f"tool.{tool_type}.{tool_name}",
        tool_type=tool_type,
        tool_name=tool_name,
    )


def get_preview_logger(token: str):
    """获取预览临时日志器，日志写入 nicegui_client_tools/_logs/{token}.log

    Args:
        token: 预览工具的唯一 token

    Returns:
        绑定了 preview 上下文的 loguru logger 实例
    """
    _PREVIEW_LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_file = _PREVIEW_LOG_DIR / f"{token}.log"

    _register_preview_sink(str(log_file), token)

    return logger.bind(
        name=f"preview.{token}",
        preview_token=token,
    )


@contextmanager
def preview_log_context(token: str):
    """预览工具执行的日志上下文管理器

    在此上下文内执行的所有代码产生的日志（包括标准 logging 被拦截转发的日志）
    都会自动附带 preview_token，从而被写入对应的预览日志文件。

    注意：对于 NiceGUI 事件回调（如按钮点击），由于回调在独立的 async context 中执行，
    ContextVar 的值不会自动继承。所以需要配合 setup_preview_logging() 使用。

    用法::

        with preview_log_context(token):
            exec(content, exec_globals)  # 用户代码内的 logging 也会写入预览日志
    """
    # 确保 sink 已注册
    get_preview_logger(token)
    # 设置 ContextVar（用于标准 logging 拦截路径）
    cv_token = _current_preview_token.set(token)
    try:
        # 同时设置 loguru contextualize（用于直接 loguru 调用路径）
        with logger.contextualize(preview_token=token):
            yield
    finally:
        _current_preview_token.reset(cv_token)


@contextmanager
def tool_log_context(tool_type: str, tool_name: str):
    """Tool 执行的日志上下文管理器

    在此上下文内执行的所有代码产生的日志（包括标准 logging 被拦截转发的日志）
    都会自动附带 tool_type + tool_name，从而被写入对应的 tool 日志文件。

    用法::

        with tool_log_context(tool_type, tool_name):
            exec(content, exec_globals)
    """
    # 确保 sink 已注册
    get_tool_logger(tool_type, tool_name)
    # 设置 ContextVar（用于标准 logging 拦截路径）
    cv_token_type = _current_tool_type.set(tool_type)
    cv_token_name = _current_tool_name.set(tool_name)
    try:
        with logger.contextualize(tool_type=tool_type, tool_name=tool_name):
            yield
    finally:
        _current_tool_type.reset(cv_token_type)
        _current_tool_name.reset(cv_token_name)


def setup_preview_logging(token: str, module_name: str):
    """为预览工具设置标准 logging 的文件 handler

    将指定模块名对应的标准 logging.Logger 直接绑定一个文件 handler，
    这样无论回调在什么时候执行，日志都会写入预览文件。

    Args:
        token: 预览 token
        module_name: 用户代码的模块名，即 exec_globals 中的 __name__
    """
    handler_key = f"preview:{token}:{module_name}"
    if handler_key in _registered_logging_handlers:
        return

    _PREVIEW_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = _PREVIEW_LOG_DIR / f"{token}.log"

    # 创建文件 handler
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # 获取用户代码对应的 logger 并添加 handler
    user_logger = logging.getLogger(module_name)
    user_logger.addHandler(file_handler)
    user_logger.setLevel(logging.DEBUG)
    # 不向上传播，避免日志重复写入主 app.log
    user_logger.propagate = False

    _registered_logging_handlers.add(handler_key)


def setup_tool_logging(tool_type: str, tool_name: str, module_name: str):
    """为 tool 设置标准 logging 的文件 handler

    Args:
        tool_type: 工具类型
        tool_name: 工具名称
        module_name: 用户代码的模块名
    """
    handler_key = f"tool:{tool_type}:{tool_name}:{module_name}"
    if handler_key in _registered_logging_handlers:
        return

    tool_log_dir = LOG_TOOLS_DIR / tool_type / tool_name
    tool_log_dir.mkdir(parents=True, exist_ok=True)
    log_file = tool_log_dir / "tool.log"

    file_handler = logging.handlers.RotatingFileHandler(
        str(log_file), maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    user_logger = logging.getLogger(module_name)
    user_logger.addHandler(file_handler)
    user_logger.setLevel(logging.DEBUG)
    # 不向上传播，避免日志重复写入主 app.log
    user_logger.propagate = False

    _registered_logging_handlers.add(handler_key)


# 记录已注册的标准 logging handlers（避免重复添加）
_registered_logging_handlers: set[str] = set()


# ── 内部：sink 注册（避免重复添加） ─────────────────────────────────────────────
_registered_sinks: set[str] = set()


def _register_tool_sink(log_path: str, tool_type: str, tool_name: str):
    """为 tool 注册独立的文件 sink"""
    if log_path in _registered_sinks:
        return

    logger.add(
        log_path,
        format=_FILE_FORMAT,
        level="DEBUG",
        rotation="5 MB",
        retention="14 days",
        compression="zip",
        encoding="utf-8",
        filter=lambda record, tt=tool_type, tn=tool_name: (
            record["extra"].get("tool_type") == tt
            and record["extra"].get("tool_name") == tn
        ),
    )
    _registered_sinks.add(log_path)


def _register_preview_sink(log_path: str, token: str):
    """为预览 token 注册独立的文件 sink"""
    if log_path in _registered_sinks:
        return

    logger.add(
        log_path,
        format=_PREVIEW_FORMAT,
        level="DEBUG",
        retention="1 day",
        encoding="utf-8",
        filter=lambda record, t=token: record["extra"].get("preview_token") == t,
    )
    _registered_sinks.add(log_path)
