"""工具变量只读访问代理。"""

from service import variable_service


class VariableProxy:
    """提供 variables['KEY'] 与 variables.get('KEY') 访问方式。"""

    def __getitem__(self, key: str) -> str:
        value = variable_service.get_variable_value(key)
        if value is None:
            raise KeyError(f"变量不存在: {key}")
        return value

    def get(self, key: str, default: object = None) -> str | object:
        """读取变量；变量不存在时返回 default。"""
        value = variable_service.get_variable_value(key)
        return default if value is None else value


variables = VariableProxy()

__all__ = ["VariableProxy", "variables"]
