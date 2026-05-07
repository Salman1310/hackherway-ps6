import importlib
import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException


class BackendFeatureTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "features.db")
        self.old_db_path = os.environ.get("SQLITE_DB_PATH")
        os.environ["SQLITE_DB_PATH"] = self.db_path
        self.connections = []

        from scripts import seed_sqlite

        importlib.reload(seed_sqlite)
        seed_sqlite.seed()

        import src.lib.sqlite as sqlite_lib

        if sqlite_lib._db is not None:
            sqlite_lib._db.close()
        sqlite_lib._db = None

    def tearDown(self):
        import src.lib.sqlite as sqlite_lib

        if sqlite_lib._db is not None:
            sqlite_lib._db.close()
        sqlite_lib._db = None

        for conn in self.connections:
            conn.close()

        if self.old_db_path is None:
            os.environ.pop("SQLITE_DB_PATH", None)
        else:
            os.environ["SQLITE_DB_PATH"] = self.old_db_path
        self.tmp.cleanup()

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        self.connections.append(conn)
        return conn


class AuthRouteTests(BackendFeatureTestCase):
    def test_login_accepts_lowercase_acf2_and_updates_last_login(self):
        from src.routes.auth import LoginRequest, login

        result = login(LoginRequest(acf2_id="arun01", password="arun123"))

        self.assertEqual("ARUN01", result["user"]["acf2_id"])
        self.assertEqual("Arun Mehta", result["user"]["name"])
        self.assertEqual("Cloud Infrastructure", result["user"]["team"])

        with self.connect() as conn:
            row = conn.execute(
                "SELECT last_login_at FROM user_auth WHERE acf2_id = 'ARUN01'"
            ).fetchone()
        self.assertIsNotNone(row["last_login_at"])

    def test_login_rejects_wrong_password(self):
        from src.routes.auth import LoginRequest, login

        with self.assertRaises(HTTPException) as ctx:
            login(LoginRequest(acf2_id="ARUN01", password="wrong"))

        self.assertEqual(401, ctx.exception.status_code)


class ConversationMemoryTests(BackendFeatureTestCase):
    def test_agent_route_creates_conversation_and_saves_user_and_bot_messages(self):
        from src.routes.agent import agent_message
        from src.types import MessageRequest, SessionState

        with patch(
            "src.routes.agent.handle_agent_message",
            return_value={
                "reply": "Hello Arun. What will your role be?",
                "session_update": {"acf2_id": "ARUN01"},
            },
        ):
            result = agent_message(
                MessageRequest(
                    content="ARUN01",
                    session=SessionState(),
                    history=[],
                    authenticated_acf2_id="ARUN01",
                )
            )

        self.assertIsNotNone(result.conversation_id)

        with self.connect() as conn:
            conversation = conn.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (result.conversation_id,),
            ).fetchone()
            messages = conn.execute(
                "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at",
                (result.conversation_id,),
            ).fetchall()

        self.assertEqual("ARUN01", conversation["acf2_id"])
        self.assertIn('"acf2_id": "ARUN01"', conversation["session_json"])
        self.assertEqual(
            [("user", "ARUN01"), ("bot", "Hello Arun. What will your role be?")],
            [(row["role"], row["content"]) for row in messages],
        )

    def test_conversation_detail_returns_messages_and_saved_session(self):
        from src.routes.conversations import get_conversation_detail

        with self.connect() as conn:
            conn.execute(
                "INSERT INTO conversations (id, acf2_id, created_at, updated_at, session_json) "
                "VALUES ('conv-1', 'ARUN01', 10, 20, ?)",
                (json.dumps({"acf2_id": "ARUN01"}),),
            )
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, created_at) "
                "VALUES ('msg-1', 'conv-1', 'user', 'ARUN01', 11)"
            )
            conn.commit()

        result = get_conversation_detail("conv-1")

        self.assertEqual("conv-1", result["conversation"]["id"])
        self.assertEqual({"acf2_id": "ARUN01"}, result["session"])
        self.assertEqual("ARUN01", result["messages"][0]["content"])


class RoleCopyTests(BackendFeatureTestCase):
    def test_copy_designation_creates_new_role_with_copied_items(self):
        from src.routes.admin import CopyDesignationRequest, copy_designation

        result = copy_designation(
            CopyDesignationRequest(
                source_designation_id="devops_cloud_engineer",
                id="devops_cloud_engineer_copy",
                title="DevOps / Cloud Engineer Copy",
                description="Copied role",
                team_hint="cloud infrastructure",
                dept_hint="technology",
            )
        )

        self.assertEqual("devops_cloud_engineer_copy", result["id"])

        with self.connect() as conn:
            source_count = conn.execute(
                "SELECT COUNT(*) AS cnt FROM role_access_items WHERE designation_id = 'devops_cloud_engineer'"
            ).fetchone()["cnt"]
            copied = conn.execute(
                "SELECT * FROM role_access_items WHERE designation_id = ? ORDER BY sort_order",
                ("devops_cloud_engineer_copy",),
            ).fetchall()

        self.assertEqual(source_count, len(copied))
        self.assertTrue(all(row["id"].startswith("devops_cloud_engineer_copy_") for row in copied))
        self.assertEqual("github_repo_access", copied[0]["access_item"])
        self.assertEqual(1, copied[0]["mandatory"])

    def test_copy_designation_rejects_duplicate_target_id(self):
        from src.routes.admin import CopyDesignationRequest, copy_designation

        with self.assertRaises(HTTPException) as ctx:
            copy_designation(
                CopyDesignationRequest(
                    source_designation_id="devops_cloud_engineer",
                    id="backend_developer",
                    title="Duplicate",
                )
            )

        self.assertEqual(409, ctx.exception.status_code)
