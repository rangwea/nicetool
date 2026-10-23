"""
数据源服务层
处理数据源的CRUD操作
"""

from datetime import datetime

from sqlmodel import select

from core.database import db_manager
from core.datasource_manager import datasource_manager
from core.logger import get_logger
from models.datasource import (
    DataSource,
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
)

logger = get_logger(__name__)


def create_datasource(datasource: DataSourceCreate) -> DataSourceResponse:
    """创建数据源"""
    try:
        with db_manager.session_scope() as session:
            # 检查名称是否已存在
            statement = select(DataSource).where(DataSource.name == datasource.name)
            existing = session.exec(statement).first()
            if existing:
                raise ValueError(f"数据源名称 '{datasource.name}' 已存在")

            # 创建数据源记录
            db_datasource = DataSource(**datasource.model_dump())
            session.add(db_datasource)
            session.commit()
            session.refresh(db_datasource)

            # 如果数据源启用,则添加到管理器
            if db_datasource.is_active and datasource_manager:
                try:
                    datasource_manager.add_datasource(db_datasource)
                except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                    logger.error(f"添加数据源到管理器失败: {e}")
                    # 回滚数据库操作
                    session.delete(db_datasource)
                    session.commit()
                    raise ValueError(f"数据源连接失败: {e!s}")

            logger.info(f"数据源 '{db_datasource.name}' 创建成功")
            return DataSourceResponse(**db_datasource.model_dump())

    except Exception as e:
        logger.error(f"创建数据源失败: {e}")
        raise


def get_datasource(datasource_id: int) -> DataSourceResponse | None:
    """获取数据源详情"""
    try:
        with db_manager.session_scope() as session:
            datasource = session.get(DataSource, datasource_id)
            if datasource:
                return DataSourceResponse(**datasource.model_dump())
            return None
    except Exception as e:
        logger.error(f"获取数据源详情失败: {e}")
        raise


def get_datasource_by_name(name: str) -> DataSourceResponse | None:
    """根据名称获取数据源"""
    try:
        with db_manager.session_scope() as session:
            statement = select(DataSource).where(DataSource.name == name)
            datasource = session.exec(statement).first()
            if datasource:
                return DataSourceResponse(**datasource.model_dump())
            return None
    except Exception as e:
        logger.error(f"获取数据源失败: {e}")
        raise


def list_datasources(
    skip: int = 0,
    limit: int = 100,
    is_active: bool | None = None,
    ds_type: str | None = None,
) -> list[DataSourceResponse]:
    """获取数据源列表"""
    try:
        with db_manager.session_scope() as session:
            statement = select(DataSource)

            # 添加过滤条件
            if is_active is not None:
                statement = statement.where(DataSource.is_active == is_active)
            if ds_type:
                statement = statement.where(DataSource.type == ds_type)

            # 分页和排序
            statement = (
                statement.offset(skip)
                .limit(limit)
                .order_by(DataSource.created_at.desc())
            )

            datasources = session.exec(statement).all()
            return [DataSourceResponse(**ds.model_dump()) for ds in datasources]

    except Exception as e:
        logger.error(f"获取数据源列表失败: {e}")
        raise


def update_datasource(
    datasource_id: int, datasource_update: DataSourceUpdate
) -> DataSourceResponse | None:
    """更新数据源"""
    try:
        with db_manager.session_scope() as session:
            datasource = session.get(DataSource, datasource_id)
            if not datasource:
                return None

            old_name = datasource.name
            old_is_active = datasource.is_active
            old_config = DataSource(**datasource.model_dump())

            # 更新字段
            update_data = datasource_update.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(datasource, key, value)

            datasource.updated_at = datetime.now()
            session.add(datasource)
            session.flush()

            # 更新管理器中的连接
            if datasource_manager:
                try:
                    # 如果名称改变,先移除旧的
                    if old_name != datasource.name:
                        datasource_manager.remove_datasource(old_name)

                    # 根据新状态处理
                    if datasource.is_active:
                        datasource_manager.reload_datasource(datasource)
                    elif old_is_active:
                        # 从启用变为禁用,移除连接
                        datasource_manager.remove_datasource(datasource.name)

                except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                    logger.error(f"更新数据源管理器失败: {e}")
                    if old_is_active:
                        try:
                            datasource_manager.reload_datasource(old_config)
                        except Exception as restore_error:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                            logger.error(f"恢复旧数据源连接失败: {restore_error}")
                    raise ValueError(f"数据源连接重载失败: {e!s}")

            logger.info(f"数据源 '{datasource.name}' 更新成功")
            return DataSourceResponse(**datasource.model_dump())

    except Exception as e:
        logger.error(f"更新数据源失败: {e}")
        raise


def delete_datasource(datasource_id: int) -> bool:
    """删除数据源"""
    try:
        with db_manager.session_scope() as session:
            datasource = session.get(DataSource, datasource_id)
            if not datasource:
                return False

            name = datasource.name

            # 从管理器中移除
            if datasource_manager and datasource.is_active:
                try:
                    datasource_manager.remove_datasource(name)
                except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                    logger.error(f"从管理器中移除数据源失败: {e}")

            # 删除数据库记录
            session.delete(datasource)
            session.commit()

            logger.info(f"数据源 '{name}' 删除成功")
            return True

    except Exception as e:
        logger.error(f"删除数据源失败: {e}")
        raise


def test_datasource_connection(datasource_id: int) -> dict:
    """测试数据源连接"""
    try:
        with db_manager.session_scope() as session:
            datasource = session.get(DataSource, datasource_id)
            if not datasource:
                return {"success": False, "message": "数据源不存在"}

            if not datasource.is_active:
                return {"success": False, "message": "数据源未启用"}

            if datasource_manager:
                success = datasource_manager.test_datasource(datasource.name)
                return {
                    "success": success,
                    "message": "连接成功" if success else "连接失败",
                }
            else:
                return {"success": False, "message": "数据源管理器未初始化"}

    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        logger.error(f"测试数据源连接失败: {e}")
        return {"success": False, "message": str(e)}
