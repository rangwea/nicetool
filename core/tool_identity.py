"""工具名称的统一校验契约。"""

import re

_NAME_PATTERN = re.compile(r"[a-z0-9_-]+")


class InvalidToolIdentity(ValueError):
    """项目名或工具名不是合法的标识符。"""


def _validate_name(value: str, label: str, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not _NAME_PATTERN.fullmatch(value)
        or len(value) > maximum
    ):
        raise InvalidToolIdentity(
            f"{label}名称不合法: {value!r}；仅支持小写字母、数字、下划线和连字符，长度不超过 {maximum}"
        )
    return value


def validate_project_name(project: str) -> str:
    return _validate_name(project, "项目", 100)


def validate_tool_identity(project: str, name: str) -> tuple[str, str]:
    return validate_project_name(project), _validate_name(name, "工具", 197)
