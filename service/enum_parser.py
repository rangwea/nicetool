"""
枚举值解析器
支持 JSON 与 Java enum 源码解析
"""

import json
import re

from models.enum_definition import normalize_enum_value

# NAME(code, "msg") — 关联紧邻其前的 Javadoc
_JAVA_ENUM_CONST = re.compile(
    r"""
    (?:/\*\*(?P<javadoc>.*?)\*/\s*)?   # 可选 Javadoc
    (?P<name>[A-Z][A-Z0-9_]*)\s*
    (?:
        \(\s*(?P<code>-?\d+)\s*,\s*"(?P<msg>[^"]*)"\s*\)   # 双参数构造
        | \(\s*"(?P<msg_only>[^"]*)"\s*\)                  # 单字符串参数
        | (?=\s*[,;])                                       # 无参常量
    )
    """,
    re.VERBOSE | re.DOTALL,
)


def parse_json_values(source: str) -> list[dict[str, str]]:
    """解析 JSON 为枚举值列表

    支持格式:
    - [{"key":"A","value":"1","remark":"说明"}]
    - {"A": "1", "B": {"value":"2","remark":"说明"}}
    """
    text = source.strip()
    if not text:
        raise ValueError("JSON 内容不能为空")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 格式错误: {exc}") from exc

    if isinstance(data, list):
        result = []
        for idx, item in enumerate(data):
            if isinstance(item, dict):
                normalized = normalize_enum_value(item)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                normalized = {
                    "key": str(item[0]),
                    "value": str(item[1]),
                    "remark": str(item[2]) if len(item) > 2 else "",
                }
            else:
                raise ValueError(f"第 {idx + 1} 项格式不支持")
            if not normalized["key"]:
                raise ValueError(f"第 {idx + 1} 项缺少 key")
            result.append(normalized)
        return result

    if isinstance(data, dict):
        result = []
        for key, val in data.items():
            if isinstance(val, dict):
                normalized = normalize_enum_value({"key": key, **val})
            else:
                normalized = {"key": str(key), "value": str(val), "remark": ""}
            result.append(normalized)
        return result

    raise ValueError("JSON 根节点须为对象或数组")


def parse_java_enum(source: str) -> list[dict[str, str]]:
    """解析 Java enum 源码为枚举值列表

    - 双参数 ``NAME(1, "垂类组")`` → key=1, value=垂类组
    - 单参数 ``NAME("说明")`` → key=NAME, value=说明
    - 无参数 ``NAME`` → key=NAME, value=NAME

    remark 取自紧邻常量前的 Javadoc 短描述（若有）
    """
    text = source.strip()
    if not text:
        raise ValueError("Java 源码不能为空")

    enum_body = _extract_enum_body(text)
    if enum_body is None:
        raise ValueError("未找到 Java enum 定义（需包含 enum EnumName { ... }）")

    constants_part = _extract_constants_section(enum_body)
    result: list[dict[str, str]] = []
    seen: set[str] = set()

    for match in _JAVA_ENUM_CONST.finditer(constants_part):
        name = match.group("name")
        if name in seen:
            continue
        seen.add(name)

        javadoc = match.group("javadoc")
        code = match.group("code")
        msg = match.group("msg") or match.group("msg_only") or ""
        remark = _javadoc_remark(javadoc)

        if code is not None:
            result.append(
                {
                    "key": str(code),
                    "value": msg,
                    "remark": remark,
                }
            )
        elif match.group("msg_only") is not None:
            result.append(
                {
                    "key": name,
                    "value": msg,
                    "remark": remark,
                }
            )
        else:
            result.append({"key": name, "value": name, "remark": remark})

    if not result:
        raise ValueError("未解析到任何枚举常量")

    return result


def _extract_enum_body(text: str) -> str | None:
    match = re.search(r"enum\s+\w+\s*\{", text)
    if not match:
        return None

    start = match.end()
    depth = 1
    end = start
    while end < len(text) and depth > 0:
        char = text[end]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        end += 1

    if depth != 0:
        raise ValueError("Java enum 花括号不匹配")

    return text[start : end - 1]


def _extract_constants_section(body: str) -> str:
    """枚举常量列表：第一个分号之前（忽略字符串与注释内的分号）"""
    depth = 0
    in_string: str | None = None
    i = 0
    while i < len(body):
        char = body[i]
        if in_string:
            if char == in_string and (i == 0 or body[i - 1] != "\\"):
                in_string = None
            i += 1
            continue
        if char in ("'", '"'):
            in_string = char
            i += 1
            continue
        if body.startswith("/*", i):
            end = body.find("*/", i + 2)
            i = len(body) if end == -1 else end + 2
            continue
        if body.startswith("//", i):
            end = body.find("\n", i)
            i = len(body) if end == -1 else end + 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == ";" and depth == 0:
            return body[:i]
        i += 1
    return body


def _javadoc_first_line(javadoc: str) -> str:
    for raw in javadoc.splitlines():
        line = raw.strip()
        if line.startswith("*"):
            line = line[1:].strip()
        if not line or line.startswith("@"):
            continue
        return line
    return ""


def _javadoc_remark(javadoc: str | None) -> str:
    """从 Javadoc 提取备注（多词取末词，过长或含标点则取整行）"""
    if not javadoc:
        return ""
    text = _javadoc_first_line(javadoc)
    if not text:
        return ""
    text = re.sub(r"\{@link[^}]*\}", "", text).strip()
    if not text:
        return ""
    if re.search(r"[，,。；;]", text):
        return text
    parts = text.split()
    if len(parts) >= 2:
        return parts[-1]
    return text


def _split_java_constants(section: str) -> list[str]:
    """按顶层逗号拆分枚举常量（保留供测试或扩展）"""
    tokens: list[str] = []
    current: list[str] = []
    depth = 0
    in_string: str | None = None

    for char in section:
        if in_string:
            current.append(char)
            if char == in_string and (len(current) < 2 or current[-2] != "\\"):
                in_string = None
            continue

        if char in ("'", '"'):
            in_string = char
            current.append(char)
            continue

        if char == "(":
            depth += 1
            current.append(char)
            continue
        if char == ")":
            depth -= 1
            current.append(char)
            continue
        if char == "," and depth == 0:
            token = "".join(current).strip()
            if token:
                tokens.append(token)
            current = []
            continue
        current.append(char)

    token = "".join(current).strip()
    if token:
        tokens.append(token)
    return tokens
