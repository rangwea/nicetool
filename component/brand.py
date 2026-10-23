"""Shared NiceTool brand components."""

from nicegui import ui


def render_brand_logo(size_class: str = "w-9 h-9", text_class: str = "text-lg") -> None:
    """Render the unified NiceTool black N logo with brand text."""
    with ui.row().classes("items-center gap-3 min-w-0"):
        ui.label("N").classes(
            f"{size_class} shrink-0 rounded-lg bg-gray-950 text-white "
            "grid place-items-center text-xl font-extrabold shadow-sm"
        )
        ui.label("NiceTool").classes(
            f"{text_class} min-w-0 truncate font-extrabold text-gray-950 tracking-tight"
        )
