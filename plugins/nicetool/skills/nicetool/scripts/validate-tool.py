"""检查工具源码契约；不导入或执行被检查文件，仅依赖标准库。"""

import argparse
import ast
import re
import tokenize
from pathlib import Path


def is_run_guard(node: ast.AST) -> bool:
    """接受模板的双入口 guard 或常见的 __main__ 等值 guard。"""
    if not isinstance(node, ast.Compare) or len(node.ops) != 1:
        return False
    if not isinstance(node.left, ast.Name) or node.left.id != "__name__":
        return False
    target = node.comparators[0]
    if isinstance(node.ops[0], ast.Eq):
        return isinstance(target, ast.Constant) and target.value == "__main__"
    if isinstance(node.ops[0], ast.In) and isinstance(
        target, (ast.Set, ast.Tuple, ast.List)
    ):
        return all(isinstance(item, ast.Constant) for item in target.elts) and {
            item.value for item in target.elts
        } == {"__main__", "__mp_main__"}
    return False


def validate_source(source: str) -> list[str]:
    """返回静态契约错误；通过不代表工具能够运行。"""
    try:
        tree = ast.parse(source)
        compile(tree, "<tool>", "exec")  # 编译但绝不执行；补充 return/await 位置检查。
    except (SyntaxError, ValueError) as exc:
        return [f"Python 语法错误：{exc}"]

    errors = []
    metadata = {}
    for line in (ast.get_docstring(tree) or "").splitlines():
        key, separator, value = line.strip().partition(":")
        if separator:
            metadata[key.strip()] = value.strip()
    for key in (
        "project",
        "name",
        "description",
        "creator",
        "created_at",
        "updated_at",
        "tags",
    ):
        if not metadata.get(key):
            errors.append(f"metadata 缺少非空字段：{key}")
    if metadata.get("tags"):
        tags = [
            tag.strip() for tag in re.split(r"[,，]", metadata["tags"]) if tag.strip()
        ]
        if not 2 <= len(tags) <= 5:
            errors.append("metadata tags 必须包含 2–5 个逗号分隔的用途词")

    mains = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "main"
    ]
    if len(mains) != 1:
        errors.append("必须定义且仅定义一个顶层 main 函数")
    elif mains[0].decorator_list:
        errors.append("顶层 main 不得使用装饰器")
    if len(mains) == 1:
        entrypoint = mains[0]
        args = entrypoint.args
        if len(args.posonlyargs) + len(args.args) > len(args.defaults) or any(
            default is None for default in args.kw_defaults
        ):
            errors.append("平台无参调用 main()，入口不得包含必填参数")
        # 嵌套函数和类中的 yield 不会把 main 变成生成器。
        pending = list(entrypoint.body)
        while pending:
            node = pending.pop()
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
            ):
                continue
            if isinstance(node, (ast.Yield, ast.YieldFrom)):
                errors.append("main 不得是生成器；平台不会迭代其返回值")
                break
            pending.extend(ast.iter_child_nodes(node))

    guards = [
        node
        for node in tree.body
        if isinstance(node, ast.If) and is_run_guard(node.test)
    ]
    if not guards:
        errors.append("缺少本地 run guard（参照 quality-gate.md）")
    else:
        for guard in guards:
            calls = [
                stmt.value
                for stmt in guard.body
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
            ]
            has_main = any(
                isinstance(call.func, ast.Name) and call.func.id == "main"
                for call in calls
            )
            has_run = any(
                isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == "ui"
                and call.func.attr == "run"
                for call in calls
            )
            if has_main and has_run:
                break
        else:
            errors.append("本地 run guard 必须包含 main() 与 ui.run(...) 调用")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        with tokenize.open(args.file) as stream:
            errors = validate_source(stream.read())
    except (OSError, UnicodeError, SyntaxError) as exc:
        parser.exit(2, f"无法读取工具源码：{exc}\n")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    print("静态检查通过；未执行源码，未验证页面或业务行为。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
