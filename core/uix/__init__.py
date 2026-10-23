"""
core.uix — 基于 NiceGUI 的扩展组件

用法::

    from core.uix.enums_select import enums_select

    sel = enums_select("ContentType", key="key", label="value", multiple=False)
"""

from core.uix.enums_select import enums_select

__all__ = ["enums_select"]
