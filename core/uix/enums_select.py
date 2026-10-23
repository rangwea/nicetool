"""
枚举下拉选择组件

从管理后台「枚举管理」读取配置，渲染 NiceGUI Select。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui
from nicegui.elements.select import Select

from core.enum_config import get_enum_values


def _build_options(
    enum_type: str,
    key: str,
    label: str,
) -> dict[str, str]:
    """NiceGUI Select 要求 dict 为 {提交值: 展示文案}。"""
    options: dict[str, str] = {}
    for item in get_enum_values(enum_type):
        opt_value = str(item.get(key, ""))
        opt_label = str(item.get(label, opt_value))
        if not opt_value:
            continue
        if opt_value in options and options[opt_value] != opt_label:
            opt_label = f"{opt_label} [{opt_value}]"
        options[opt_value] = opt_label
    return options


def enums_select(
    enum_type: str,
    *,
    key: str = "key",
    label: str = "value",
    multiple: bool = False,
    value: str | list[str] | None = None,
    on_change: Callable[..., Any] | None = None,
    field_label: str | None = None,
    with_input: bool = True,
    use_chips: bool | None = None,
    **select_kwargs: Any,
) -> Select:
    """枚举下拉 / 多选组件

    Args:
        enum_type: 枚举管理中的名称，如 ``ContentType``
        key: 枚举项中作为提交值的字段名，默认 ``key``
        label: 枚举项中作为展示文案的字段名，默认 ``value``
        multiple: ``False`` 单选，``True`` 多选
        value: 初始选中值（单选为 str，多选为 list[str]）
        on_change: 值变化回调
        field_label: 表单项标签（传给 ``ui.select`` 的 ``label``）
        with_input: 是否可输入筛选
        use_chips: 多选时是否显示 chips，默认多选时为 True
        **select_kwargs: 其余参数原样传给 ``ui.select``

    Returns:
        NiceGUI ``Select`` 实例；``.value`` 为选中的 key（多选时为 list）

    Example::

        from core.uix.enums_select import enums_select

        ct = enums_select(
            "ContentType",
            key="key",
            label="value",
            multiple=False,
            field_label="内容组别",
        )
        ui.button("提交", on_click=lambda: print(ct.value))
    """
    options = _build_options(enum_type, key, label)
    if not options:
        raise KeyError(f"枚举 '{enum_type}' 无可用选项，请先在管理后台配置")

    if value is None:
        value = [] if multiple else None

    chips = use_chips if use_chips is not None else multiple

    element = ui.select(
        options=options,
        label=field_label,
        value=value,
        multiple=multiple,
        on_change=on_change,
        with_input=with_input,
        **select_kwargs,
    )

    props: list[str] = ["outlined", "dense", "color=primary"]
    if chips and multiple:
        props.append("use-chips")
    element.props(" ".join(props))

    element._enum_type = enum_type  # type: ignore[attr-defined]
    element._enum_key_field = key  # type: ignore[attr-defined]
    element._enum_label_field = label  # type: ignore[attr-defined]

    return element
