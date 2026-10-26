"""显式初始化独立演示数据库；预置源码不同时写入新版本。"""

import os
from pathlib import Path


def validate_demo_target(enabled: bool, database: str) -> None:
    if not enabled or database != "nicetool_demo":
        raise ValueError(
            "演示初始化仅允许 NICETOOL_DEMO=true 且 MYSQL_DATABASE=nicetool_demo"
        )


def seed_tools(storage, sources: dict[str, str]) -> dict[str, int]:
    result = {"created": 0, "updated": 0, "skipped": 0}
    for name, content in sources.items():
        current = storage.load_current("demo", name)
        if current == content:
            result["skipped"] += 1
            continue
        status = "created" if current is None else "updated"
        saved = storage.save_current("demo", name, content, created_by="demo-seed")
        if not saved.get("success"):
            raise RuntimeError(f"演示工具初始化失败: {name}")
        result[status] += 1
    return result


def main() -> None:
    # 在任何数据库连接之前检查显式开关，避免普通部署意外导入演示内容。
    validate_demo_target(
        os.environ.get("NICETOOL_DEMO", "").lower() == "true",
        os.environ.get("MYSQL_DATABASE", ""),
    )
    from sqlmodel import select

    import models  # noqa: F401 — 注册全部 SQLModel 表
    from core.database import db_manager
    from models.nicetool_environment import NiceToolEnvironment
    from service.tool_storage import get_tool_storage

    try:
        db_manager.create_tables()
        root = Path(__file__).resolve().parents[1] / "examples/demo/tools"
        sources = {
            path.stem: path.read_text(encoding="utf-8")
            for path in sorted(root.glob("*.py"))
        }
        if len(sources) != 3:
            raise RuntimeError("演示工具文件不完整")
        print(seed_tools(get_tool_storage(), sources))
        with db_manager.session_scope() as session:
            # 保留用户修改；只在环境列表为空时创建默认环境。
            if session.exec(select(NiceToolEnvironment)).first() is None:
                session.add(
                    NiceToolEnvironment(
                        name="demo",
                        url=os.environ.get("DEMO_PUBLIC_URL", "http://localhost:8000"),
                        token_env="NICETOOL_DEMO_TOKEN",
                        is_default=True,
                        remark="本机演示环境；未启用认证，不用于生产",
                    )
                )
    finally:
        db_manager.close()


if __name__ == "__main__":
    main()
