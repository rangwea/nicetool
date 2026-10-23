import unittest
from unittest.mock import patch

from public.user.index import _tool_display_name, use_tool


class UserToolIndexTest(unittest.TestCase):
    def test_display_name_prefers_metadata_title(self):
        tool = {"name": "sign_multiple_records_query", "title": "多签约项目查询"}

        self.assertEqual(_tool_display_name(tool), "多签约项目查询")

    @patch("public.user.index.ui.navigate.to")
    def test_use_tool_navigates_with_filename_identifier(self, navigate):
        tool = {
            "project": "c2-purchase",
            "name": "sign_multiple_records_query",
            "title": "多签约项目查询",
        }

        use_tool(tool)

        navigate.assert_called_once_with(
            "/user/tools/c2-purchase/sign_multiple_records_query"
        )


if __name__ == "__main__":
    unittest.main()
