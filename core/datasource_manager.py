"""
数据源管理器
统一管理MySQL和MongoDB数据源的连接池和访问接口
"""

from contextlib import contextmanager
from zoneinfo import ZoneInfo

from pymongo import MongoClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlmodel import Session, select

from core.database import db_manager
from core.logger import get_logger
from models.datasource import DataSource

logger = get_logger(__name__)


class DatabaseWrapper:
    """数据库连接包装器基类"""

    def __init__(self, config: DataSource):
        self.config = config
        self.client = None

    def connect(self):
        """建立连接"""
        raise NotImplementedError

    def disconnect(self):
        """断开连接"""
        raise NotImplementedError

    def test_connection(self) -> bool:
        """测试连接"""
        raise NotImplementedError

    def get_client(self):
        """获取客户端连接"""
        return self.client


class MySQLWrapper(DatabaseWrapper):
    """MySQL连接包装器"""

    def connect(self):
        """建立MySQL连接"""
        try:
            url = self._build_connection_url()
            self.client = create_engine(
                url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size or 10,
                max_overflow=self.config.max_overflow or 20,
                pool_timeout=self.config.pool_timeout or 30,
                pool_recycle=self.config.pool_recycle or 3600,
                echo=False,
                future=True,
            )
            logger.info(f"MySQL数据源 '{self.config.name}' 连接成功")
        except Exception as e:
            logger.error(f"MySQL数据源 '{self.config.name}' 连接失败: {e}")
            raise

    def _build_connection_url(self) -> str:
        """构建MySQL连接URL"""
        charset = self.config.charset or "utf8mb4"
        return (
            f"mysql+pymysql://{self.config.username}:{self.config.password}"
            f"@{self.config.host}:{self.config.port}/{self.config.database}"
            f"?charset={charset}"
        )

    def disconnect(self):
        """断开MySQL连接"""
        if self.client:
            self.client.dispose()
            logger.info(f"MySQL数据源 '{self.config.name}' 已断开")

    def test_connection(self) -> bool:
        """测试MySQL连接"""
        try:
            with self.client.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            logger.error(f"MySQL数据源 '{self.config.name}' 连接测试失败: {e}")
            return False

    @contextmanager
    def session_scope(self):
        """获取MySQL会话上下文"""

        session = Session(self.client)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class MongoDBWrapper(DatabaseWrapper):
    """MongoDB连接包装器"""

    def connect(self):
        """建立MongoDB连接"""
        try:
            url = self._build_connection_url()
            options = {
                "minPoolSize": self.config.min_pool_size or 0,
                "maxPoolSize": self.config.max_pool_size or 100,
                "serverSelectionTimeoutMS": 5000,
            }
            if self.config.timezone:
                options.update(
                    tz_aware=True,
                    tzinfo=ZoneInfo(self.config.timezone),
                )
            self.client = MongoClient(url, **options)
            self.client.admin.command("ping")
            logger.info(f"MongoDB数据源 '{self.config.name}' 连接成功")
        except Exception as e:
            logger.error(f"MongoDB数据源 '{self.config.name}' 连接失败: {e}")
            raise

    def _build_connection_url(self) -> str:
        """构建MongoDB连接URL"""
        auth_source = self.config.auth_source or "admin"
        url = (
            f"mongodb://{self.config.username}:{self.config.password}"
            f"@{self.config.host}:{self.config.port}/{self.config.database}"
            f"?authSource={auth_source}"
        )
        if self.config.replica_set:
            url += f"&replicaSet={self.config.replica_set}"
        return url

    def disconnect(self):
        """断开MongoDB连接"""
        if self.client:
            self.client.close()
            logger.info(f"MongoDB数据源 '{self.config.name}' 已断开")

    def test_connection(self) -> bool:
        """测试MongoDB连接"""
        try:
            self.client.admin.command("ping")
            return True
        except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            logger.error(f"MongoDB数据源 '{self.config.name}' 连接测试失败: {e}")
            return False

    def get_database(self):
        """获取MongoDB数据库对象"""
        if self.client:
            return self.client[self.config.database]
        return None


class DataSourceManager:
    """数据源管理器"""

    def __init__(self):
        self._connections: dict[str, DatabaseWrapper] = {}
        self._load_datasources()

    def _load_datasources(self):
        """从数据库加载所有激活的数据源"""
        try:
            if db_manager is None:
                logger.warning("数据库管理器未初始化,无法加载数据源配置")
                return

            with db_manager.session_scope() as session:
                statement = select(DataSource).where(DataSource.is_active)
                datasources = session.exec(statement).all()

                # 在会话内初始化所有连接
                for ds in datasources:
                    try:
                        # 确保所有属性都在会话内访问
                        # 创建一个新的DataSource对象,复制所有属性
                        ds_copy = DataSource(
                            id=ds.id,
                            name=ds.name,
                            type=ds.type,
                            host=ds.host,
                            port=ds.port,
                            username=ds.username,
                            password=ds.password,
                            database=ds.database,
                            description=ds.description,
                            is_active=ds.is_active,
                            charset=ds.charset,
                            pool_size=ds.pool_size,
                            max_overflow=ds.max_overflow,
                            pool_timeout=ds.pool_timeout,
                            pool_recycle=ds.pool_recycle,
                            auth_source=ds.auth_source,
                            replica_set=ds.replica_set,
                            min_pool_size=ds.min_pool_size,
                            max_pool_size=ds.max_pool_size,
                            timezone=ds.timezone,
                            created_at=ds.created_at,
                            updated_at=ds.updated_at,
                        )
                        self._init_connection(ds_copy)
                    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                        logger.error(f"初始化数据源 '{ds.name}' 失败: {e}")

            logger.info(f"成功加载 {len(self._connections)} 个数据源")

        except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            logger.error(f"加载数据源配置失败: {e}")

    def _init_connection(self, config: DataSource):
        """初始化数据源连接"""
        if config.type == "mysql":
            wrapper = MySQLWrapper(config)
        elif config.type == "mongodb":
            wrapper = MongoDBWrapper(config)
        else:
            raise ValueError(f"不支持的数据源类型: {config.type}")

        wrapper.connect()
        self._connections[config.name] = wrapper

    def add_datasource(self, config: DataSource):
        """添加新数据源"""
        try:
            self._init_connection(config)
            logger.info(f"数据源 '{config.name}' 添加成功")
        except Exception as e:
            logger.error(f"添加数据源 '{config.name}' 失败: {e}")
            raise

    def remove_datasource(self, name: str):
        """移除数据源"""
        if name in self._connections:
            self._connections[name].disconnect()
            del self._connections[name]
            logger.info(f"数据源 '{name}' 已移除")

    def reload_datasource(self, config: DataSource):
        """重新加载数据源"""
        self.remove_datasource(config.name)
        self.add_datasource(config)

    def get_datasource(self, name: str) -> DatabaseWrapper | None:
        """获取数据源连接"""
        return self._connections.get(name)

    def test_datasource(self, name: str) -> bool:
        """测试数据源连接"""
        wrapper = self.get_datasource(name)
        if wrapper:
            return wrapper.test_connection()
        return False

    def __getitem__(self, name: str):
        """支持db['datasource_name']语法"""
        wrapper = self.get_datasource(name)
        if wrapper is None:
            raise KeyError(f"数据源 '{name}' 不存在")

        if isinstance(wrapper, MySQLWrapper):
            return wrapper.get_client()
        elif isinstance(wrapper, MongoDBWrapper):
            return wrapper.get_database()

        return wrapper.get_client()

    def get_mysql_session(self, name: str):
        """获取MySQL会话上下文管理器"""
        wrapper = self.get_datasource(name)
        if not isinstance(wrapper, MySQLWrapper):
            raise TypeError(f"数据源 '{name}' 不是MySQL类型")
        return wrapper.session_scope()

    def close_all(self):
        """关闭所有数据源连接"""
        for name, wrapper in self._connections.items():
            try:
                wrapper.disconnect()
            except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                logger.error(f"关闭数据源 '{name}' 失败: {e}")
        self._connections.clear()
        logger.info("所有数据源连接已关闭")


# 创建全局数据源管理器实例
try:
    datasource_manager = DataSourceManager()
except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
    logger.warning(f"数据源管理器初始化失败: {e}")
    datasource_manager = None


# 提供全局db访问接口
class DBProxy:
    """数据库代理类,提供db['name']访问方式"""

    def __getitem__(self, name: str):
        if datasource_manager is None:
            raise RuntimeError("数据源管理器未初始化")
        return datasource_manager[name]

    def get_mysql_session(self, name: str):
        """获取MySQL会话"""
        if datasource_manager is None:
            raise RuntimeError("数据源管理器未初始化")
        return datasource_manager.get_mysql_session(name)


# 全局db对象
db = DBProxy()

__all__ = ["DBProxy", "DataSourceManager", "datasource_manager", "db"]
