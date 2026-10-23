"""
数据源管理控制器
提供数据源的CRUD操作、连接测试等功能
"""

from typing import Any

from nicegui import ui

from core.i18n import html_t, option_labels, t
from core.logger import get_logger
from models.datasource import DataSourceCreate, DataSourceUpdate
from public.admin.base_controller import BaseController, Menu
from service import datasource_service

# 获取日志器
logger = get_logger(__name__)


class DataSourceController(BaseController):
    """数据源管理控制器"""

    def __init__(self):
        super().__init__()
        self.datasources_data = []
        self.search_query = ""
        self.type_filter = "all"
        self.status_filter = "all"
        self.selected_datasource = None

    def menu(self) -> Menu:
        return Menu(icon="storage", label="数据源管理", color="primary")

    def render(self):
        """渲染数据源管理页面"""
        # 初始化数据
        self.refresh_data()

        with ui.column().classes("w-full gap-3"):
            # 页面标题和操作按钮
            with ui.row().classes("w-full justify-between items-start gap-3 flex-wrap"):
                with ui.column().classes("gap-0.5"):
                    ui.label(t("数据源管理")).classes(
                        "text-lg font-semibold app-text-primary"
                    )
                    ui.label(t("维护连接配置并检查数据源可用状态")).classes(
                        "text-xs text-gray-500"
                    )
                with ui.row().classes("gap-2"):
                    ui.button(t("刷新数据"), on_click=self.refresh_data).props(
                        "color=grey-7 outline dense"
                    )
                    ui.button(t("新增数据源"), on_click=self.show_create_dialog).props(
                        "color=primary dense"
                    )

            # 搜索和筛选区域
            with (
                ui.card().classes("w-full").props("flat"),
                ui.card_section().classes("w-full py-3 px-3 sm:px-4"),
                ui.row().classes("w-full gap-2 items-center flex-wrap"),
            ):
                # 搜索框
                ui.input(
                    placeholder=t("搜索数据源名称或描述..."),
                    on_change=self.on_search_change,
                ).props("outlined dense color=primary clearable").classes(
                    "min-w-[14rem] flex-1"
                )
                # 数据源类型筛选
                ui.select(
                    options=option_labels(
                        {
                            "all": "全部类型",
                            "mysql": "MySQL",
                            "mongodb": "MongoDB",
                        }
                    ),
                    value="all",
                    on_change=self.on_type_filter_change,
                ).props("outlined dense color=primary").classes("min-w-[10rem]")
                # 状态筛选
                ui.select(
                    options=option_labels(
                        {
                            "all": "全部状态",
                            "active": "启用",
                            "inactive": "禁用",
                        }
                    ),
                    value="all",
                    on_change=self.on_status_filter_change,
                ).props("outlined dense color=primary").classes("min-w-[10rem]")

                # 操作按钮
                ui.button(t("重置"), on_click=self.reset_filters).props(
                    "color=grey-7 flat dense size=sm"
                ).classes("ml-auto")

            # 表格区域
            with ui.card().classes("w-full").props("flat"):
                self.render_datasource_table()

    @ui.refreshable
    def render_datasource_table(self):
        """渲染数据源表格"""
        filtered_data = self.get_filtered_datasources()

        if not filtered_data:
            with ui.column().classes("w-full items-center py-10 gap-1.5"):
                ui.icon("storage").classes("text-4xl text-gray-300")
                ui.label(t("暂无数据源")).classes("text-sm font-medium text-gray-700")
                ui.label(t('点击上方"新增数据源"按钮开始添加')).classes(
                    "text-sm text-gray-400"
                )
            return

        # 表格列定义
        columns = [
            {
                "name": "name",
                "label": t("数据源名称"),
                "field": "name",
                "align": "left",
                "sortable": True,
            },
            {"name": "type", "label": t("类型"), "field": "type", "align": "center"},
            {"name": "host", "label": t("主机地址"), "field": "host", "align": "left"},
            {"name": "port", "label": t("端口"), "field": "port", "align": "center"},
            {
                "name": "database",
                "label": t("数据库"),
                "field": "database",
                "align": "left",
            },
            {
                "name": "status",
                "label": t("状态"),
                "field": "is_active",
                "align": "center",
            },
            {
                "name": "created_at",
                "label": t("创建时间"),
                "field": "created_at",
                "align": "center",
                "sortable": True,
            },
            {
                "name": "actions",
                "label": t("操作"),
                "field": "actions",
                "align": "center",
            },
        ]

        # 创建表格
        table = (
            ui.table(columns=columns, rows=filtered_data, row_key="id")
            .props("color=primary flat dense separator=horizontal")
            .classes("w-full")
        )

        # 自定义类型列
        table.add_slot(
            "body-cell-type",
            """
            <q-td :props="props">
                <span class="text-grey-8">{{ props.value.toUpperCase() }}</span>
            </q-td>
        """,
        )

        # 自定义状态列
        table.add_slot(
            "body-cell-status",
            html_t("""
            <q-td :props="props">
                <q-badge
                    :color="props.value ? 'positive' : 'negative'"
                    :label="props.value ? '启用' : '禁用'"
                />
            </q-td>
        """),
        )

        # 自定义创建时间列
        table.add_slot(
            "body-cell-created_at",
            """
            <q-td :props="props">
                {{ new Date(props.value).toLocaleString('zh-CN') }}
            </q-td>
        """,
        )

        # 自定义操作列
        table.add_slot(
            "body-cell-actions",
            html_t("""
            <q-td :props="props">
                <div class="q-gutter-xs">
                    <q-btn
                        icon="cable"
                        color="info"
                        flat
                        round
                        size="sm"
                        @click="$parent.$emit('test', props.row)"
                    >
                        <q-tooltip>测试连接</q-tooltip>
                    </q-btn>
                    <q-btn
                        icon="edit"
                        color="primary"
                        flat
                        round
                        size="sm"
                        @click="$parent.$emit('edit', props.row)"
                    >
                        <q-tooltip>编辑</q-tooltip>
                    </q-btn>
                    <q-btn
                        icon="delete"
                        color="negative"
                        flat
                        round
                        size="sm"
                        @click="$parent.$emit('delete', props.row)"
                    >
                        <q-tooltip>删除</q-tooltip>
                    </q-btn>
                </div>
            </q-td>
        """),
        )

        # 绑定事件
        table.on("test", self.test_datasource_connection)
        table.on("edit", self.edit_datasource)
        table.on("delete", self.delete_datasource)

    def get_datasource_stats(self) -> dict[str, int]:
        """获取数据源统计信息"""
        total = len(self.datasources_data)
        active = len([ds for ds in self.datasources_data if ds.get("is_active", False)])
        mysql = len([ds for ds in self.datasources_data if ds.get("type") == "mysql"])
        mongodb = len(
            [ds for ds in self.datasources_data if ds.get("type") == "mongodb"]
        )

        return {"total": total, "active": active, "mysql": mysql, "mongodb": mongodb}

    def get_filtered_datasources(self) -> list[dict[str, Any]]:
        """获取过滤后的数据源列表"""
        filtered = self.datasources_data.copy()

        # 搜索过滤
        if self.search_query:
            filtered = [
                ds
                for ds in filtered
                if self.search_query.lower() in ds.get("name", "").lower()
                or self.search_query.lower() in ds.get("description", "").lower()
            ]

        # 类型过滤
        if self.type_filter != "all":
            filtered = [ds for ds in filtered if ds.get("type") == self.type_filter]

        # 状态过滤
        if self.status_filter != "all":
            is_active = self.status_filter == "active"
            filtered = [ds for ds in filtered if ds.get("is_active") == is_active]

        return filtered

    def refresh_data(self):
        """刷新数据源数据"""
        try:
            datasources = datasource_service.list_datasources()
            self.datasources_data = [ds.model_dump() for ds in datasources]

            self.render_datasource_table.refresh()

            ui.notify(t("数据已刷新"), type="positive")
        except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            self.logger.error(f"刷新数据源数据失败: {e}")
            ui.notify(t("刷新数据失败: {arg0}", arg0=str(e)), type="negative")

    def on_search_change(self, e):
        """搜索条件变化"""
        self.search_query = e.value
        self.render_datasource_table.refresh()

    def on_type_filter_change(self, e):
        """类型筛选变化"""
        self.type_filter = e.value
        self.render_datasource_table.refresh()

    def on_status_filter_change(self, e):
        """状态筛选变化"""
        self.status_filter = e.value
        self.render_datasource_table.refresh()

    def reset_filters(self):
        """重置所有筛选条件"""
        self.search_query = ""
        self.type_filter = "all"
        self.status_filter = "all"

        # 刷新表格
        self.render_datasource_table.refresh()

        ui.notify(t("筛选条件已重置"), type="info")

    def show_create_dialog(self):
        """显示创建数据源对话框"""
        type_controls: dict[str, Any] = {}

        def on_type_change(e):
            """数据源类型变化时的处理"""
            mysql_config = type_controls.get("mysql_config")
            mongodb_config = type_controls.get("mongodb_config")
            port_input = type_controls.get("port_input")
            if not mysql_config or not mongodb_config or not port_input:
                return

            is_mysql = e.value == "mysql"
            mysql_config.set_visibility(is_mysql)
            mongodb_config.set_visibility(not is_mysql)
            port_input.value = 3306 if is_mysql else 27017

        with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
            ui.label(t("新增数据源")).classes("text-lg font-semibold mb-4")

            with ui.column().classes("w-full gap-4"):
                # 基本信息
                name_input = (
                    ui.input(t("数据源名称"))
                    .props("outlined required")
                    .classes("w-full")
                )
                type_select = (
                    ui.select(
                        ["mysql", "mongodb"],
                        label=t("数据源类型"),
                        value="mysql",
                        on_change=on_type_change,
                    )
                    .props("outlined required")
                    .classes("w-full")
                )
                description_input = (
                    ui.textarea(t("描述信息")).props("outlined").classes("w-full")
                )

                # 连接信息
                with ui.row().classes("w-full gap-4"):
                    host_input = (
                        ui.input(t("主机地址"), value="localhost")
                        .props("outlined required")
                        .classes("flex-1")
                    )
                    port_input = (
                        ui.number(t("端口"), value=3306, min=1, max=65535)
                        .props("outlined required")
                        .classes("w-32")
                    )
                    type_controls["port_input"] = port_input

                with ui.row().classes("w-full gap-4"):
                    username_input = (
                        ui.input(t("用户名"))
                        .props("outlined required")
                        .classes("flex-1")
                    )
                    password_input = (
                        ui.input(t("密码"), password=True)
                        .props("outlined required")
                        .classes("flex-1")
                    )

                database_input = (
                    ui.input(t("数据库名称"))
                    .props("outlined required")
                    .classes("w-full")
                )

                # MySQL特有配置
                mysql_config = ui.column().classes("w-full gap-4")
                with mysql_config:
                    ui.label(t("MySQL配置")).classes(
                        "text-md font-medium text-gray-700"
                    )
                    with ui.row().classes("w-full gap-4"):
                        charset_input = (
                            ui.input(t("字符集"), value="utf8mb4")
                            .props("outlined")
                            .classes("flex-1")
                        )
                        pool_size_input = (
                            ui.number(t("连接池大小"), value=10, min=1, max=100)
                            .props("outlined")
                            .classes("w-32")
                        )
                    type_controls["mysql_config"] = mysql_config

                # MongoDB特有配置
                mongodb_config = ui.column().classes("w-full gap-4")
                with mongodb_config:
                    ui.label(t("MongoDB配置")).classes(
                        "text-md font-medium text-gray-700"
                    )
                    with ui.row().classes("w-full gap-4"):
                        auth_source_input = (
                            ui.input(t("认证数据库"), value="admin")
                            .props("outlined")
                            .classes("flex-1")
                        )
                        replica_set_input = (
                            ui.input(t("副本集名称"))
                            .props("outlined")
                            .classes("flex-1")
                        )
                    timezone_input = (
                        ui.input(
                            t("读取时区"),
                            placeholder=t("例如 Asia/Shanghai；留空使用驱动默认值"),
                        )
                        .props("outlined clearable")
                        .classes("w-full")
                    )
                    type_controls["mongodb_config"] = mongodb_config

                # 状态开关
                is_active_switch = ui.switch(t("启用数据源"), value=True).classes(
                    "mb-4"
                )

                mongodb_config.set_visibility(False)

                # 按钮区域
                with ui.row().classes("w-full justify-end gap-2 mt-6"):
                    ui.button(t("取消"), on_click=dialog.close).props("flat")
                    ui.button(
                        t("创建"),
                        on_click=lambda: self.create_datasource(
                            dialog,
                            name_input,
                            type_select,
                            description_input,
                            host_input,
                            port_input,
                            username_input,
                            password_input,
                            database_input,
                            charset_input,
                            pool_size_input,
                            auth_source_input,
                            replica_set_input,
                            timezone_input,
                            is_active_switch,
                        ),
                    ).props("color=primary")

        dialog.open()

    def create_datasource(
        self,
        dialog,
        name_input,
        type_select,
        description_input,
        host_input,
        port_input,
        username_input,
        password_input,
        database_input,
        charset_input,
        pool_size_input,
        auth_source_input,
        replica_set_input,
        timezone_input,
        is_active_switch,
    ):
        """创建数据源"""
        try:
            # 验证必填字段
            if not all(
                [
                    name_input.value,
                    type_select.value,
                    host_input.value,
                    port_input.value,
                    username_input.value,
                    password_input.value,
                    database_input.value,
                ]
            ):
                ui.notify(t("请填写所有必填字段"), type="warning")
                return

            # 构建创建数据
            create_data = {
                "name": name_input.value,
                "type": type_select.value,
                "description": description_input.value,
                "host": host_input.value,
                "port": int(port_input.value),
                "username": username_input.value,
                "password": password_input.value,
                "database": database_input.value,
                "is_active": is_active_switch.value,
            }

            # 添加类型特有配置
            if type_select.value == "mysql":
                create_data.update(
                    {
                        "charset": charset_input.value or "utf8mb4",
                        "pool_size": int(pool_size_input.value)
                        if pool_size_input.value
                        else 10,
                    }
                )
            elif type_select.value == "mongodb":
                create_data.update(
                    {
                        "auth_source": auth_source_input.value or "admin",
                        "replica_set": replica_set_input.value,
                        "timezone": timezone_input.value.strip()
                        if timezone_input.value
                        else None,
                    }
                )

            # 调用服务创建数据源
            datasource_create = DataSourceCreate(**create_data)
            result = datasource_service.create_datasource(datasource_create)

            ui.notify(t("数据源 '{arg0}' 创建成功", arg0=result.name), type="positive")
            dialog.close()
            self.refresh_data()

        except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            self.logger.error(f"创建数据源失败: {e}")
            ui.notify(t("创建失败: {arg0}", arg0=str(e)), type="negative")

    def edit_datasource(self, e):
        """编辑数据源"""
        datasource = e.args
        self.selected_datasource = datasource

        with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
            ui.label(t("编辑数据源 - {arg0}", arg0=datasource["name"])).classes(
                "text-lg font-semibold mb-4"
            )

            with ui.column().classes("w-full gap-4"):
                # 基本信息
                name_input = (
                    ui.input(t("数据源名称"), value=datasource.get("name", ""))
                    .props("outlined required")
                    .classes("w-full")
                )
                description_input = (
                    ui.textarea(t("描述信息"), value=datasource.get("description", ""))
                    .props("outlined")
                    .classes("w-full")
                )

                # 连接信息
                with ui.row().classes("w-full gap-4"):
                    host_input = (
                        ui.input(t("主机地址"), value=datasource.get("host", ""))
                        .props("outlined required")
                        .classes("flex-1")
                    )
                    port_input = (
                        ui.number(
                            t("端口"),
                            value=datasource.get("port", 3306),
                            min=1,
                            max=65535,
                        )
                        .props("outlined required")
                        .classes("w-32")
                    )

                with ui.row().classes("w-full gap-4"):
                    username_input = (
                        ui.input(t("用户名"), value=datasource.get("username", ""))
                        .props("outlined required")
                        .classes("flex-1")
                    )
                    password_input = (
                        ui.input(
                            t("密码"),
                            password=True,
                            value=datasource.get("password", ""),
                        )
                        .props("outlined required")
                        .classes("flex-1")
                    )

                database_input = (
                    ui.input(t("数据库名称"), value=datasource.get("database", ""))
                    .props("outlined required")
                    .classes("w-full")
                )

                timezone_input = None
                if datasource.get("type") == "mongodb":
                    timezone_input = (
                        ui.input(
                            t("读取时区"),
                            value=datasource.get("timezone") or "",
                            placeholder=t("例如 Asia/Shanghai；留空使用驱动默认值"),
                        )
                        .props("outlined clearable")
                        .classes("w-full")
                    )

                # 状态开关
                is_active_switch = ui.switch(
                    t("启用数据源"), value=datasource.get("is_active", True)
                ).classes("mb-4")

                # 按钮区域
                with ui.row().classes("w-full justify-end gap-2 mt-6"):
                    ui.button(t("取消"), on_click=dialog.close).props("flat")
                    ui.button(
                        t("保存"),
                        on_click=lambda: self.update_datasource(
                            dialog,
                            datasource["id"],
                            name_input,
                            description_input,
                            host_input,
                            port_input,
                            username_input,
                            password_input,
                            database_input,
                            timezone_input,
                            is_active_switch,
                        ),
                    ).props("color=primary")

        dialog.open()

    def update_datasource(
        self,
        dialog,
        datasource_id,
        name_input,
        description_input,
        host_input,
        port_input,
        username_input,
        password_input,
        database_input,
        timezone_input,
        is_active_switch,
    ):
        """更新数据源"""
        try:
            # 验证必填字段
            if not all(
                [
                    name_input.value,
                    host_input.value,
                    port_input.value,
                    username_input.value,
                    password_input.value,
                    database_input.value,
                ]
            ):
                ui.notify(t("请填写所有必填字段"), type="warning")
                return

            # 构建更新数据
            update_data = {
                "name": name_input.value,
                "description": description_input.value,
                "host": host_input.value,
                "port": int(port_input.value),
                "username": username_input.value,
                "password": password_input.value,
                "database": database_input.value,
                "is_active": is_active_switch.value,
            }
            if timezone_input is not None:
                update_data["timezone"] = (
                    timezone_input.value.strip() if timezone_input.value else None
                )

            # 调用服务更新数据源
            datasource_update = DataSourceUpdate(**update_data)
            result = datasource_service.update_datasource(
                datasource_id, datasource_update
            )

            if result:
                ui.notify(
                    t("数据源 '{arg0}' 更新成功", arg0=result.name), type="positive"
                )
                dialog.close()
                self.refresh_data()
            else:
                ui.notify(t("数据源不存在"), type="warning")

        except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            self.logger.error(f"更新数据源失败: {e}")
            ui.notify(t("更新失败: {arg0}", arg0=str(e)), type="negative")

    def delete_datasource(self, e):
        """删除数据源"""
        datasource = e.args

        with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
            ui.label(t("确认删除")).classes("text-lg font-semibold mb-4")
            ui.label(
                t("确定要删除数据源 '{arg0}' 吗？", arg0=datasource["name"])
            ).classes("text-gray-600 mb-6")
            ui.label(t("此操作不可撤销！")).classes("text-red-500 text-sm mb-4")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button(t("取消"), on_click=dialog.close).props("flat")
                ui.button(
                    t("删除"),
                    on_click=lambda: self.confirm_delete_datasource(
                        dialog, datasource["id"], datasource["name"]
                    ),
                ).props("color=negative")

        dialog.open()

    def confirm_delete_datasource(self, dialog, datasource_id, datasource_name):
        """确认删除数据源"""
        try:
            success = datasource_service.delete_datasource(datasource_id)

            if success:
                ui.notify(
                    t("数据源 '{arg0}' 删除成功", arg0=datasource_name), type="positive"
                )
                dialog.close()
                self.refresh_data()
            else:
                ui.notify(t("数据源不存在"), type="warning")

        except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            self.logger.error(f"删除数据源失败: {e}")
            ui.notify(t("删除失败: {arg0}", arg0=str(e)), type="negative")

    def test_datasource_connection(self, e):
        """测试数据源连接"""
        datasource = e.args

        try:
            ui.notify(t("正在测试连接..."), type="info")
            result = datasource_service.test_datasource_connection(datasource["id"])

            if result["success"]:
                ui.notify(
                    t("数据源 '{arg0}' 连接成功", arg0=datasource["name"]),
                    type="positive",
                )
            else:
                ui.notify(
                    t("连接失败: {arg0}", arg0=result["message"]), type="negative"
                )

        except Exception as exc:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            self.logger.error(f"测试数据源连接失败: {exc}")
            ui.notify(t("连接测试失败: {arg0}", arg0=str(exc)), type="negative")


# 创建控制器实例
datasource_controller = DataSourceController()
