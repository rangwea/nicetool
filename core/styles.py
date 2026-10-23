"""NiceTool 固定应用样式。"""

from nicegui import app, ui

BRAND_COLORS = {
    "primary": "#1F2937",
    "secondary": "#3B82F6",
    "tertiary": "#8B5CF6",
    "accent": "#8B5CF6",
    "positive": "#059669",
    "negative": "#DC2626",
    "warning": "#D97706",
    "info": "#0284C7",
}

GLOBAL_CSS = """
<style>
    :root {
        --q-primary: #1F2937;
        --q-secondary: #3B82F6;
        --q-tertiary: #8B5CF6;
        --q-accent: #8B5CF6;
        --q-positive: #059669;
        --q-negative: #DC2626;
        --q-warning: #D97706;
        --q-info: #0284C7;
        --app-background: #F8FAFC;
        --app-surface: #FFFFFF;
        --app-text: #1F2937;
        --app-primary: #1F2937;
        --app-secondary: #3B82F6;
        --app-primary-light: rgba(31, 41, 55, 0.10);
        --app-secondary-light: rgba(59, 130, 246, 0.10);
        --app-primary-soft: rgba(31, 41, 55, 0.10);
        --app-primary-hover: rgba(31, 41, 55, 0.05);
    }

    html, body {
        margin: 0 !important;
        padding: 0 !important;
    }

    body {
        min-height: 100vh;
        background: var(--app-background) !important;
        color: var(--app-text) !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            "Helvetica Neue", Arial, sans-serif;
    }

    *, *::before, *::after { box-sizing: border-box; }
    .nicegui-content { margin: 0 !important; padding: 0 !important; }

    .app-text-primary { color: var(--app-text) !important; }
    .app-text-secondary { color: var(--app-secondary) !important; }
    .app-bg-primary-light { background-color: var(--app-primary-light) !important; }
    .app-bg-secondary-light { background-color: var(--app-secondary-light) !important; }
    .app-border-primary { border-color: var(--app-primary) !important; }
    .app-border-secondary { border-color: var(--app-secondary) !important; }
    .app-menu-hover:hover { background-color: var(--app-primary-hover) !important; }
    .app-menu-active {
        color: var(--q-primary) !important;
        background-color: var(--app-primary-soft) !important;
        border-left: 4px solid var(--q-primary) !important;
    }

    .nicegui-content .q-card {
        border: 1px solid #F3F4F6;
        border-radius: 8px;
        background: var(--app-surface);
        box-shadow: none;
        transition: border-color 0.15s ease-in-out;
    }
    .nicegui-content .q-card:hover { border-color: #E5E7EB; }

    .nicegui-content .q-btn {
        border-radius: 6px;
        box-shadow: none;
        font-size: 0.875rem;
        font-weight: 500;
        letter-spacing: 0.025em;
        text-transform: none;
        transition: background-color 0.15s ease-in-out,
            border-color 0.15s ease-in-out, color 0.15s ease-in-out;
    }
    .nicegui-content .q-btn:hover,
    .nicegui-content .q-btn:active { box-shadow: none; transform: none; }

    .nicegui-content .q-field--outlined .q-field__control {
        border-radius: 6px;
        background: var(--app-surface);
    }
    .nicegui-content .q-field--outlined .q-field__control::before {
        border-color: #E5E7EB;
    }
    .nicegui-content .q-field--outlined.q-field--focused .q-field__control::before {
        border-color: var(--q-primary);
        border-width: 2px;
    }

    .nicegui-content .q-avatar { background-color: inherit; color: inherit; }
    .nicegui-content .q-avatar.bg-blue-100 { background: #DBEAFE; color: #1E40AF; }
    .nicegui-content .q-avatar.bg-green-100 { background: #DCFCE7; color: #166534; }
    .nicegui-content .q-avatar.bg-purple-100 { background: #F3E8FF; color: #7C2D12; }
    .nicegui-content .q-avatar.bg-orange-100 { background: #FED7AA; color: #9A3412; }
    .nicegui-content .q-avatar.bg-red-100 { background: #FEE2E2; color: #991B1B; }
    .nicegui-content .q-avatar.bg-yellow-100 { background: #FEF3C7; color: #92400E; }
    .nicegui-content .q-avatar.bg-pink-100 { background: #FCE7F3; color: #BE185D; }
    .nicegui-content .q-avatar.bg-indigo-100 { background: #E0E7FF; color: #3730A3; }
    .nicegui-content .q-avatar.bg-gray-100 { background: #F3F4F6; color: #374151; }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(243, 244, 246, 0.5); }
    ::-webkit-scrollbar-thumb { background: #9CA3AF; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #6B7280; }

    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.5rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        line-height: 1;
    }
    .status-success { background: #DCFCE7; color: #166534; }
    .status-warning { background: #FEF3C7; color: #92400E; }
    .status-error { background: #FEE2E2; color: #991B1B; }
    .status-info { background: #DBEAFE; color: #1E40AF; }
    .status-neutral { background: #F3F4F6; color: #374151; }
</style>
"""


def apply_app_styles() -> None:
    """应用固定品牌色、全局 CSS 和组件默认值。"""
    app.config.quasar_config["brand"].update(BRAND_COLORS)

    field_props = 'outlined dense color="primary" bg-color="white"'
    for element in (ui.input, ui.textarea, ui.number, ui.select, ui.date_input):
        element.default_props(field_props)
        element.default_classes("rounded-md transition-colors duration-150")

    ui.button.default_props("unelevated no-caps")
    ui.button.default_classes(
        "rounded-md font-medium tracking-wide transition-colors duration-150"
    )
    ui.card.default_props("flat")
    ui.card.default_classes("rounded-lg border border-gray-100 shadow-none")
    ui.checkbox.default_props('color="primary"')
    ui.radio.default_props('color="primary"')
    ui.switch.default_props('color="primary"')
    ui.avatar.default_props('color=""')
    ui.expansion.default_props(
        'header-class="rounded-t-lg border-b border-gray-100" '
        'expand-icon-class="text-primary"'
    )
    ui.expansion.default_classes(
        "rounded-lg border border-gray-100 shadow-none overflow-hidden mb-4"
    )

    ui.add_head_html(GLOBAL_CSS, shared=True)
