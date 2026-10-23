from unittest import TestCase
from unittest.mock import patch

from public.api.variable_api import list_variable_keys


class VariableApiTest(TestCase):
    def test_list_response_never_contains_values(self):
        with patch(
            "public.api.variable_api.variable_service.list_variable_keys",
            return_value=[
                {"key": "API_BASE", "remark": "接口地址", "value": "secret-value"}
            ],
        ):
            response = list_variable_keys(search="API")

        self.assertEqual(
            response.model_dump(),
            {
                "variables": [{"key": "API_BASE", "remark": "接口地址"}],
                "total": 1,
            },
        )
