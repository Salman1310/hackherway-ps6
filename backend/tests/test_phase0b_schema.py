import importlib
import os
import sqlite3
import tempfile
import unittest


class Phase0BSchemaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "phase0b.db")
        self.old_db_path = os.environ.get("SQLITE_DB_PATH")
        os.environ["SQLITE_DB_PATH"] = self.db_path
        self.connections = []

    def tearDown(self):
        for conn in self.connections:
            conn.close()
        if self.old_db_path is None:
            os.environ.pop("SQLITE_DB_PATH", None)
        else:
            os.environ["SQLITE_DB_PATH"] = self.old_db_path
        self.tmp.cleanup()

    def _seeded_db(self):
        from scripts import seed_sqlite

        importlib.reload(seed_sqlite)
        seed_sqlite.seed()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        self.connections.append(conn)
        return conn

    def test_seed_creates_phase0b_normalized_schema(self):
        conn = self._seeded_db()

        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        self.assertEqual(
            {
                "users",
                "user_designations",
                "designations",
                "role_access_items",
                "access_requests",
                "approval_events",
                "approver_routing",
                "audit_log",
                "privilege_edges",
                "dangerous_combinations",
                "template_drafts",
                "conversations",
                "messages",
            },
            tables,
        )

        designation_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(designations)")
        }
        self.assertEqual(
            {"id", "title", "description", "team_hint", "dept_hint"},
            designation_columns,
        )
        self.assertNotIn("mandatory_items", designation_columns)
        self.assertNotIn("optional_items", designation_columns)

        role_item_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(role_access_items)")
        }
        self.assertTrue(
            {
                "id",
                "designation_id",
                "access_item",
                "display_name",
                "system",
                "description",
                "mandatory",
                "owner_team",
                "servicenow_catalog_item_id",
                "sort_order",
            }.issubset(role_item_columns)
        )

    def test_seed_maps_only_arun_and_neha_to_designations(self):
        conn = self._seeded_db()

        mappings = {
            row["acf2_id"]: row["designation_id"]
            for row in conn.execute(
                "SELECT acf2_id, designation_id FROM user_designations"
            ).fetchall()
        }

        self.assertEqual(
            {
                "ARUN01": "devops_cloud_engineer",
                "NEHA02": "finance_analyst",
            },
            mappings,
        )

    def test_seed_creates_queryable_role_access_rows_with_catalog_ids(self):
        conn = self._seeded_db()

        devops_rows = conn.execute(
            """
            SELECT access_item, display_name, system, mandatory,
                   servicenow_catalog_item_id, sort_order
            FROM role_access_items
            WHERE designation_id = 'devops_cloud_engineer'
            ORDER BY sort_order
            """
        ).fetchall()

        self.assertGreaterEqual(len(devops_rows), 8)
        self.assertEqual("github_repo_access", devops_rows[0]["access_item"])
        self.assertEqual(1, devops_rows[0]["mandatory"])
        self.assertTrue(devops_rows[0]["display_name"])
        self.assertTrue(devops_rows[0]["system"])
        self.assertTrue(devops_rows[0]["servicenow_catalog_item_id"])


if __name__ == "__main__":
    unittest.main()
