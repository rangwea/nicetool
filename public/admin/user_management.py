"""用户与登录权限管理。"""

from nicegui import ui

from core.auth.service import auth_service
from core.i18n import html_t, option_labels, t
from public.admin.base_controller import BaseController, Menu
from service.access_control_service import get_user_projects, update_user_projects
from service.tool_manage_service import list_tool_projects


class UserManagementController(BaseController):
    def menu(self) -> Menu:
        return Menu(icon="manage_accounts", label="用户管理", color="primary")

    def render(self):
        with ui.column().classes("w-full gap-3"):
            with ui.row().classes("w-full items-start justify-between gap-3 flex-wrap"):
                with ui.column().classes("gap-0.5"):
                    ui.label(t("用户管理")).classes(
                        "text-lg font-semibold app-text-primary"
                    )
                    ui.label(t("创建账号、调整角色、禁用账号及重置临时密码")).classes(
                        "text-sm text-gray-500"
                    )
                ui.button(t("创建用户"), on_click=self._show_create_dialog).props(
                    "color=primary dense"
                )
            self._render_users()

    @ui.refreshable
    def _render_users(self):
        users = auth_service.list_users()
        with ui.card().classes("w-full p-0 overflow-hidden").props("flat"):
            columns = [
                {
                    "name": "username",
                    "label": t("用户"),
                    "field": "username",
                    "align": "left",
                },
                {
                    "name": "email",
                    "label": t("邮箱"),
                    "field": "email",
                    "align": "left",
                },
                {"name": "role", "label": t("角色"), "field": "role", "align": "left"},
                {
                    "name": "status",
                    "label": t("状态"),
                    "field": "status",
                    "align": "left",
                },
                {
                    "name": "actions",
                    "label": t("操作"),
                    "field": "actions",
                    "align": "right",
                },
            ]
            rows = [
                {
                    "id": user.id,
                    "username": user.display_name or user.username,
                    "email": user.email or "-",
                    "role": user.role,
                    "status": t("启用" if user.is_active else "禁用"),
                    "is_active": user.is_active,
                }
                for user in users
            ]
            table = (
                ui.table(columns=columns, rows=rows, row_key="id")
                .classes("w-full")
                .props("flat dense separator=horizontal color=primary")
            )
            table.add_slot(
                "body-cell-actions",
                html_t("""
                <q-td :props="props"><q-btn flat dense no-caps color="primary" label="切换角色" @click="$parent.$emit('role', props.row)" /><q-btn v-if="props.row.role !== 'admin'" flat dense no-caps color="secondary" label="项目授权" @click="$parent.$emit('projects', props.row)" /><q-btn flat dense no-caps color="warning" :label="props.row.is_active ? '禁用' : '启用'" @click="$parent.$emit('status', props.row)" /><q-btn flat dense no-caps color="secondary" label="重置密码" @click="$parent.$emit('reset', props.row)" /></q-td>
            """),
            )
            table.on("role", lambda event: self._toggle_role(event.args))
            table.on("projects", lambda event: self._show_projects_dialog(event.args))
            table.on("status", lambda event: self._toggle_status(event.args))
            table.on("reset", lambda event: self._reset_password(event.args))

    def _show_create_dialog(self):
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
            ui.label(t("创建用户")).classes("text-base font-semibold px-4 pt-4")
            with ui.column().classes("w-full gap-3 px-4"):
                username = (
                    ui.input(t("用户名"))
                    .props("outlined dense color=primary")
                    .classes("w-full")
                )
                email = (
                    ui.input(t("邮箱"))
                    .props("outlined dense color=primary type=email")
                    .classes("w-full")
                )
                role = (
                    ui.select(
                        option_labels({"user": "普通用户", "admin": "管理员"}),
                        value="user",
                        label=t("角色"),
                    )
                    .props("outlined dense color=primary")
                    .classes("w-full")
                )

            def submit():
                try:
                    _, password = auth_service.create_user_with_temporary_password(
                        username.value or "", email.value or "", role.value or "user"
                    )
                except ValueError as exc:
                    ui.notify(str(exc), type="negative")
                    return
                dialog.close()
                self._render_users.refresh()
                self._show_password(password)

            with ui.row().classes("w-full justify-end gap-2 px-4 pb-4"):
                ui.button(t("取消"), on_click=dialog.close).props(
                    "flat dense color=grey-7"
                )
                ui.button(t("创建"), on_click=submit).props("dense color=primary")
        dialog.open()

    def _show_password(self, password: str):
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-md p-4 gap-3"):
            ui.label(t("一次性临时密码")).classes("text-base font-semibold")
            ui.label(t("请立即安全地交给用户，关闭后不再显示。")).classes(
                "text-sm text-amber-700"
            )
            ui.input(value=password).props("readonly outlined dense").classes(
                "w-full font-mono"
            )
            ui.button(t("完成"), on_click=dialog.close).props(
                "dense color=primary"
            ).classes("self-end")
        dialog.open()

    def _toggle_role(self, row):
        try:
            auth_service.update_user_access(
                row["id"], role="user" if row["role"] == "admin" else "admin"
            )
        except ValueError as exc:
            ui.notify(str(exc), type="negative")
            return
        self._render_users.refresh()

    def _show_projects_dialog(self, row):
        project_options = list_tool_projects()
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl p-4 gap-3"):
            ui.label(t("项目授权：{arg0}", arg0=row["username"])).classes(
                "text-base font-semibold"
            )
            projects = (
                ui.select(
                    project_options,
                    value=[
                        project
                        for project in get_user_projects(row["id"])
                        if project in project_options
                    ],
                    label=t("可访问项目"),
                    multiple=True,
                )
                .props("outlined dense use-chips")
                .classes("w-full")
            )

            def submit():
                try:
                    update_user_projects(row["id"], projects.value or [])
                except (ValueError, RuntimeError) as exc:
                    ui.notify(str(exc), type="negative")
                    return
                dialog.close()
                ui.notify(t("项目授权已保存"), type="positive")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button(t("取消"), on_click=dialog.close).props("flat dense")
                ui.button(t("保存"), on_click=submit).props("color=primary dense")
        dialog.open()

    def _toggle_status(self, row):
        try:
            auth_service.update_user_access(row["id"], is_active=not row["is_active"])
        except ValueError as exc:
            ui.notify(str(exc), type="negative")
            return
        self._render_users.refresh()

    def _reset_password(self, row):
        self._show_password(auth_service.reset_user_password(row["id"]))


user_management_controller = UserManagementController()
