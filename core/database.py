"""
MySQL数据库连接管理
使用SQLModel和SQLAlchemy进行数据库操作
"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.pool import QueuePool
from sqlmodel import Session, SQLModel, create_engine

from core.logger import get_logger
from core.settings import settings

# 获取日志器
logger = get_logger(__name__)


class DatabaseManager:
    """数据库管理器"""

    def __init__(self):
        self.engine = None
        self._initialize_engine()

    def _initialize_engine(self):
        """初始化数据库引擎"""
        try:
            mysql_config = settings.get_mysql_config()

            self.engine = create_engine(
                mysql_config["url"],
                poolclass=QueuePool,
                pool_size=mysql_config["pool_size"],
                max_overflow=mysql_config["max_overflow"],
                pool_timeout=mysql_config["pool_timeout"],
                pool_recycle=mysql_config["pool_recycle"],
                echo=settings.debug,  # 在调试模式下打印SQL语句
                future=True,
            )

            logger.info("MySQL数据库引擎初始化成功")

        except Exception as e:
            logger.error(f"MySQL数据库引擎初始化失败: {e}")
            self.engine = None
            raise

    def create_tables(self):
        """创建数据库表"""
        try:
            if self.engine is None:
                raise RuntimeError("数据库引擎未初始化")

            SQLModel.metadata.create_all(self.engine)
            logger.info("数据库表创建成功")

        except Exception as e:
            logger.error(f"创建数据库表失败: {e}")
            raise

    def get_session(self) -> Session:
        """获取数据库会话"""
        if self.engine is None:
            raise RuntimeError("数据库引擎未初始化")

        return Session(self.engine)

    @contextmanager
    def session_scope(self) -> Generator[Session]:
        """数据库会话上下文管理器"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            from sqlalchemy import text

            with self.session_scope() as session:
                session.exec(text("SELECT 1"))
            logger.info("数据库连接测试成功")
            return True
        except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            logger.error(f"数据库连接测试失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            logger.info("数据库连接已关闭")


# 创建全局数据库管理器实例
try:
    db_manager = DatabaseManager()
except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
    logger.warning(f"数据库管理器初始化失败: {e}")
    db_manager = None

__all__ = ["DatabaseManager", "db_manager"]
