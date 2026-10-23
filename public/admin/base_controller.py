from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.logger import get_logger


@dataclass
class Menu:
    icon: str
    label: str
    color: str


class BaseController(ABC):
    """控制器基类 - 提供通用UI操作"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def menu(self) -> Menu:
        """菜单项"""

    @abstractmethod
    def render(self):
        """渲染页面"""
