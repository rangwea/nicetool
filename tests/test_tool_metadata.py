import unittest

from service.tool_metadata import parse_tool_metadata


class ToolMetadataTest(unittest.TestCase):
    def test_parses_normalized_docstring_fields(self):
        content = '''"""
        Name: Sales Dashboard
        description: Revenue: monthly trend
        Tags: sales, finance
        """
'''

        self.assertEqual(
            parse_tool_metadata(content),
            {
                "name": "Sales Dashboard",
                "description": "Revenue: monthly trend",
                "tags": "sales, finance",
            },
        )

    def test_returns_empty_metadata_without_module_docstring(self):
        self.assertEqual(parse_tool_metadata("VALUE = 1\n"), {})

    def test_propagates_invalid_python_syntax(self):
        with self.assertRaises(SyntaxError):
            parse_tool_metadata("def broken(:\n")


if __name__ == "__main__":
    unittest.main()
