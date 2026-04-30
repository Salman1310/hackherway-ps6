import json
import unittest
from unittest.mock import patch

from src.agent.index import ROLE_SYSTEM_PROMPT, handle_agent_message
from src.types import SessionState, WorkdayContext


def _session(acf2_id="ARUN01", team="Cloud Infrastructure", dept="Technology"):
    return SessionState(
        acf2_id=acf2_id,
        workday_context=WorkdayContext(
            name="Arun Mehta",
            team=team,
            manager="Raj Kumar",
            dept=dept,
            employment_type="full-time",
        ),
    )


def _tool_use_response(sql, tool_use_id="tool-1"):
    return {
        "stopReason": "tool_use",
        "output": {
            "message": {
                "content": [
                    {
                        "toolUse": {
                            "name": "query_db",
                            "toolUseId": tool_use_id,
                            "input": {"sql": sql},
                        }
                    }
                ]
            }
        },
    }


def _end_turn_response(text):
    return {
        "stopReason": "end_turn",
        "output": {"message": {"content": [{"text": text}]}},
    }


class Phase2RoleResolverTests(unittest.TestCase):
    def test_role_prompt_uses_normalized_tables_not_json_context(self):
        prompt = ROLE_SYSTEM_PROMPT.lower()

        self.assertIn("role_access_items", prompt)
        self.assertIn("user_designations", prompt)
        self.assertIn("do not context-stuff", prompt)
        self.assertNotIn("mandatory_items", prompt)
        self.assertNotIn("optional_items", prompt)

    def test_direct_role_match_returns_selected_template_session_update(self):
        designation_rows = [
            {
                "id": "backend_developer",
                "title": "Backend Developer",
                "description": "Builds server-side services and APIs",
                "team_hint": "backend, engineering, api",
                "dept_hint": "technology",
            }
        ]
        access_rows = [
            {
                "id": "backend_developer:github_repo_access",
                "designation_id": "backend_developer",
                "access_item": "github_repo_access",
                "display_name": "GitHub repository access",
                "system": "GitHub",
                "description": "Required for source code work",
                "mandatory": 1,
                "owner_team": "Engineering Tools",
                "servicenow_catalog_item_id": "SN-GITHUB-REPO",
                "sort_order": 10,
            },
            {
                "id": "backend_developer:github_copilot",
                "designation_id": "backend_developer",
                "access_item": "github_copilot",
                "display_name": "GitHub Copilot",
                "system": "GitHub",
                "description": "Optional coding assistant",
                "mandatory": 0,
                "owner_team": "Engineering Tools",
                "servicenow_catalog_item_id": "SN-GITHUB-COPILOT",
                "sort_order": 50,
            },
        ]

        def fake_query(sql):
            lowered = sql.lower()
            if "from designations" in lowered:
                return json.dumps(designation_rows)
            if "from role_access_items" in lowered:
                return json.dumps(access_rows)
            if "insert into user_designations" in lowered:
                return json.dumps({"success": True, "rows_affected": 1})
            return "[]"

        responses = [
            _tool_use_response("SELECT * FROM designations WHERE title LIKE '%Backend%'"),
            _tool_use_response(
                "SELECT * FROM role_access_items WHERE designation_id = 'backend_developer'",
                "tool-2",
            ),
            _end_turn_response(
                "I matched your role to Backend Developer and prepared the access template."
            ),
        ]

        with patch("src.agent.index.converse_with_tools", side_effect=responses), patch(
            "src.agent.index._mcp_query_db", side_effect=fake_query
        ), patch("src.agent.index._mcp_execute_db", side_effect=fake_query):
            result = handle_agent_message(
                "I am a backend developer",
                _session(),
                [],
            )

        update = result["session_update"]
        self.assertEqual("Backend Developer", update["resolved_role"]["role"])
        self.assertEqual("backend_developer", update["selected_template"]["id"])
        self.assertEqual(1, len(update["selected_template"]["mandatory_access"]))
        self.assertEqual(1, len(update["selected_template"]["optional_access"]))
        self.assertEqual(
            "github_repo_access",
            update["selected_template"]["mandatory_access"][0]["id"],
        )
        self.assertEqual(
            update["selected_template"]["mandatory_access"],
            update["final_bundle"],
        )

    def test_vague_role_question_does_not_update_template(self):
        with patch(
            "src.agent.index.converse_with_tools",
            return_value=_end_turn_response(
                "Can you share the closest role title or the system area you will support?"
            ),
        ):
            result = handle_agent_message("I do stuff", _session(), [])

        self.assertNotIn("session_update", result)
        self.assertIn("role", result["reply"].lower())

    def test_no_match_reply_does_not_update_template(self):
        with patch(
            "src.agent.index.converse_with_tools",
            return_value=_end_turn_response(
                "I could not match that role to an access template yet. I will need an admin to review it."
            ),
        ):
            result = handle_agent_message("I am a quantum pastry lead", _session("SARA03"), [])

        self.assertNotIn("session_update", result)
        self.assertIn("could not match", result["reply"].lower())


if __name__ == "__main__":
    unittest.main()
