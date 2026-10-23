# NiceTool 数据源访问

在工具使用平台 MySQL/MongoDB 数据源时加载。以下表、字段和数据源名称仅为示例，
必须替换为已确认的业务 schema；不要把示例结构当作真实数据库。

## 发现与边界

按 `SKILL.md` 解析实际 skill 目录，在用户工作目录执行：

```bash
python "$NICETOOL_SKILL_ROOT/scripts/tool-cli.py" --json databases --type mysql
python "$NICETOOL_SKILL_ROOT/scripts/tool-cli.py" --json databases --type mongodb
```

- `databases` 列出平台数据源；不假定它能返回表、集合或字段结构。
- 从用户提供的 schema 或已知业务代码确定字段；结构不明时澄清，避免猜测后写入。
- 使用 `from core.datasource_manager import db`，不在工具中构造连接串或复制凭据。
- 在业务函数运行时访问代理，不在模块顶层查询、读取配置或建立连接。
- 数据源不可用时记录异常，页面给出友好提示并恢复控件，不自动切换其他环境。

## MySQL 查询与事务

```python
from sqlalchemy import text
from core.datasource_manager import db


def query_orders(status: str, page: int, page_size: int) -> tuple[list[dict], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    params = {"status": status, "limit": page_size, "offset": (page - 1) * page_size}
    with db.get_mysql_session("orders_mysql") as session:
        total = session.execute(
            text("SELECT COUNT(*) FROM orders WHERE status = :status"), params
        ).scalar_one()
        rows = (
            session.execute(
                text(
                    "SELECT id, status FROM orders WHERE status = :status "
                    "ORDER BY id DESC LIMIT :limit OFFSET :offset"
                ),
                params,
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows], int(total)
```

- `db.get_mysql_session(name)` 返回会话上下文管理器；正常退出自动 commit，异常自动
  rollback，最终 close。不把 session、游标或 ORM 延迟加载对象带出工作函数。
- 值使用绑定参数；表名、字段名、排序方向从固定映射白名单选择，不能绑定或拼接任意用户输入。
- count 与 rows 使用相同筛选和权限条件，稳定排序包含唯一键。并发写入时不承诺总数永远不变。
- 写入也放在同一个 session 上下文内。用已确认的记录 ID 和必要业务条件约束 UPDATE/DELETE，
  检查受影响行数；不为预览页面自动执行业务写入。

## MongoDB 查询与序列化

```python
from core.datasource_manager import db


def query_events(status: str, page: int, page_size: int) -> tuple[list[dict], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    collection = db["events_mongo"]["events"]
    query = {"status": status}  # status 是已校验的字符串，不接收用户提供的操作符对象。
    total = collection.count_documents(query)
    cursor = collection.find(query, {"_id": 1, "status": 1}).sort("_id", -1)
    rows = list(cursor.skip((page - 1) * page_size).limit(page_size))
    return [
        {"id": str(row["_id"]), "status": row.get("status", "")} for row in rows
    ], total
```

- `db[name]` 对 MongoDB 返回 Database；继续按集合名索引。不要关闭平台共享 client。
- 使用固定字段构造 filter/projection；不要把任意 JSON 直接当查询条件或更新表达式。
- 大偏移量查询按业务需要使用基于稳定唯一键的游标分页；不要先拉全量再切片。
- UI 接收普通 dict/list/scalar。ObjectId 转字符串，日期按业务时区格式化，Decimal
  按精度要求转换；不要直接传 cursor、Row 或未序列化的数据库对象。
- 写入使用明确的 filter 和 `$set` 等已定义操作；跨文档原子性取决于部署与事务能力，
  不把 MySQL 会话事务语义套用到 MongoDB。

## 异步调用和授权

```python
from nicegui import run

rows, total = await run.io_bound(query_orders, submitted_status, page, page_size)
```

在完整同步工作函数内部打开并关闭会话，不在 UI 线程创建 session 后传给工作线程。
筛选和页码传普通值快照，不在后台函数访问 UI 控件。权限、租户和行范围必须来自实际
业务身份并进入数据查询条件，不能信任浏览器提交的租户 ID。未明确身份接口时先查项目
现有实现，不虚构平台鉴权能力。业务写入需有对应操作授权；发布工具本身不授权写业务数据。
