"""工具源码元数据解析。"""

import ast


def parse_tool_metadata(content: str) -> dict[str, str]:
    """解析模块 docstring 中的 ``key: value`` 元数据。"""
    docstring = ast.get_docstring(ast.parse(content))
    if not docstring:
        return {}

    metadata: dict[str, str] = {}
    for raw_line in docstring.splitlines():
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip().lower()] = value.strip()
    return metadata
