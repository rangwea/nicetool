"""Use the configured platform language for NiceGUI built-in components."""

from nicegui import ui

from core.i18n import get_locale


class localized_page(ui.page):
    def resolve_language(self):
        return get_locale()
