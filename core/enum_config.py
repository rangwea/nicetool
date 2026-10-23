"""
枚举配置访问（工具侧）

在管理后台「枚举管理」中维护的枚举，可在工具中按名称读取::

    from core.enum_config import enum_select_options, enum_label, get_enum_values

    ui.select(enum_select_options("ContentType"), label="内容组别")
    ui.label(enum_label("ContentType", "1"))  # 显示 value，如 垂类组
"""

from __future__ import annotations

from typing import Any

from service import enum_service

_cache: dict[str, list[dict[str, str]]] = {}


def clear_enum_cache(name: str | None = None) -> None:
    """清除内存缓存；后台修改枚举后可在工具内调用以拉取最新数据"""
    if name is None:
        _cache.clear()
    else:
        _cache.pop(name, None)


def get_enum_values(name: str, *, use_cache: bool = True) -> list[dict[str, str]]:
    """按名称获取枚举项列表，每项含 key / value / remark"""
    if use_cache and name in _cache:
        return [dict(item) for item in _cache[name]]

    record = enum_service.get_enum_definition_by_name(name)
    if not record:
        raise KeyError(f"未找到枚举配置: {name}")

    values = [dict(item) for item in (record.values or [])]
    if use_cache:
        _cache[name] = values
    return values


def enum_select_options(
    name: str,
    *,
    label_field: str = "value",
    value_field: str = "key",
    include_remark: bool = False,
) -> dict[str, str]:
    """生成 NiceGUI ui.select 可用的 options 映射（提交值 -> 展示文案）

    默认提交值用 key（如「1」），展示文案用 value（如「垂类组」）。
    """
    options: dict[str, str] = {}
    for item in get_enum_values(name):
        display = str(item.get(label_field, ""))
        submit = str(item.get(value_field, ""))
        if include_remark and item.get("remark"):
            display = f"{display} ({item['remark']})"
        if not submit:
            continue
        if submit in options and options[submit] != display:
            display = f"{display} [{submit}]"
        options[submit] = display
    return options


def enum_label(name: str, key: str, *, default: str = "") -> str:
    """根据 key 取展示用 value"""
    for item in get_enum_values(name):
        if str(item.get("key")) == str(key):
            return str(item.get("value", default))
    return default


def enum_remark(name: str, key: str, *, default: str = "") -> str:
    """根据 key 取备注"""
    for item in get_enum_values(name):
        if str(item.get("key")) == str(key):
            return str(item.get("remark", default))
    return default


def enum_key_by_value(name: str, value: str, *, default: str = "") -> str:
    """根据 value 反查 key"""
    for item in get_enum_values(name):
        if str(item.get("value")) == str(value):
            return str(item.get("key", default))
    return default


def enum_as_dict(name: str, *, field: str = "value") -> dict[str, str]:
    """key -> field 的字典，field 通常为 value 或 remark"""
    return {
        str(item["key"]): str(item.get(field, "")) for item in get_enum_values(name)
    }


def get_enum_meta(name: str) -> dict[str, Any] | None:
    """获取枚举元信息（含 description）"""
    record = enum_service.get_enum_definition_by_name(name)
    return record.model_dump() if record else None
