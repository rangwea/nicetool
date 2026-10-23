import re
import unittest
from pathlib import Path

from sqlmodel import SQLModel

import models  # noqa: F401


class InitSqlSchemaTest(unittest.TestCase):
    def test_init_sql_contains_every_sqlmodel_table(self):
        init_sql = (
            Path(__file__).resolve().parents[1] / "scripts" / "init.sql"
        ).read_text(encoding="utf-8")
        ddl_tables = set(
            re.findall(
                r"CREATE TABLE IF NOT EXISTS\s+`?([A-Za-z0-9_]+)`?",
                init_sql,
                re.IGNORECASE,
            )
        )

        self.assertEqual(set(SQLModel.metadata.tables) - ddl_tables, set())


if __name__ == "__main__":
    unittest.main()
