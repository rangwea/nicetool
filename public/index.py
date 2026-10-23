"""NiceTool application entry page."""

from nicegui import ui

from component.language import localized_page
from core.logger import get_logger
from core.settings import settings

logger = get_logger(__name__)


@localized_page("/")
def index() -> None:
    """Redirect the product root to the tool center."""
    logger.info("访问首页")
    ui.navigate.to(settings.path_for("/user"))
