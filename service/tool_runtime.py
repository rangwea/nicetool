"""NiceTool 工具入口校验与加载。"""

import ast
import importlib.util
import inspect
from collections.abc import Callable
from typing import Any


class ToolEntryPointError(ValueError):
    """工具没有有效的顶层 ``main()`` 入口。"""


def validate_tool_entrypoint(content: str) -> bool:
    """校验源码并返回 ``main()`` 是否为异步函数。"""
    tree = ast.parse(content)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return False
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "main":
            return True
    raise ToolEntryPointError("工具必须定义顶层 main() 函数")


def load_tool_entrypoint(
    module_name: str, filepath: str
) -> tuple[Callable[..., Any], bool]:
    """从工具文件加载可调用的同步或异步 ``main()``。"""
    with open(filepath, encoding="utf-8") as source:
        content = source.read()
    validate_tool_entrypoint(content)

    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None or spec.loader is None:
        raise ToolEntryPointError("无法创建工具模块加载器")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    main = getattr(module, "main", None)
    if not callable(main):
        raise ToolEntryPointError("工具的 main 必须是可调用函数")
    return main, inspect.iscoroutinefunction(main)
