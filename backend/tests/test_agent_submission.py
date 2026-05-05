"""
Phase 3 submission flow tests.

Covers:
  - routing: selected_template present -> submission phase
  - routing: no selected_template -> role phase (not submission)
  - successful execute_db on access_requests -> request_id in session_update
  - execute_db on unrelated table -> no session_update
  - Bedrock failure during submission -> fallback reply
"""

import json
import unittest
from unittest.mock import patch

from src.agent.index import handle_agent_message
from src.types import SessionState, WorkdayContext


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_WORKDAY = WorkdayContext(
    name="Arun Mehta",
    team="Cloud Infrastructure",
    manager="Raj Kumar",
    dept="Technology",
    employment_type="full-time",
)

_SELECTED_TEMPLATE = {
    "id": "devops_cloud_engineer",
    "name": "DevOps / Cloud Engineer",
    "description": "Cloud infra role",
    "confidence": 0.96,
    "reasoning": "Team and role match",
    "mandatory_access": [
        {"id": "github_repo_access", "name": "GitHub repository access",
         "system": "GitHub", "reason": "Source control", "mandatory": True},
        {"id": "jira_project_access", "name": "Jira project access",
         "system": "Jira", "reason": "Issue tracking", "mandatory": True},
    ],
    "optional_access": [
        {"id": "pagerduty", "name": "PagerDuty",
         "system": "PagerDuty", "reason": "On-call alerting", "mandatory": False},
    ],
}

_SESSION_WITH_TEMPLATE = SessionState(
    acf2_id="ARUN01",
    workday_context=_WORKDAY,
    selected_template=_SELECTED_TEMPLATE,
    final_bundle=_SELECTED_TEMPLATE["mandatory_access"],
)

_SESSION_WITHOUT_TEMPLATE = SessionState(
    acf2_id="ARUN01",
    workday_context=_WORKDAY,
    selected_template=None,
)


def _end_turn_response(text: str) -> dict:
    return {
        "stopReason": "end_turn",
        "output": {"message": {"content": [{"text": text}]}},
    }


def _tool_use_response(tool_name: str, tool_input: dict, use_id: str = "tu-001") -> dict:
    return {
        "stopReason": "tool_use",
        "output": {
            "message": {
                "content": [
                    {"toolUse": {"name": tool_name, "input": tool_input, "toolUseId": use_id}}
                ]
            }
        },
    }


# ---------------------------------------------------------------------------
# Routing tests
# ---------------------------------------------------------------------------

class TestSubmissionRouting(unittest.TestCase):

    def test_selected_template_routes_to_submission_phase(self):
        """When selected_template is set, handle_agent_message must not call role phase."""
        with patch("src.agent.index.converse_with_tools") as mock_converse:
            mock_converse.return_value = _end_turn_response(
                "Which optional items would you like?"
            )
            result = handle_agent_message(
                "I want to submit my access request",
                _SESSION_WITH_TEMPLATE,
                [],
            )

        mock_converse.assert_called_once()
        # Submission phase uses SUBMISSION_TOOL_SPECS (2 tools); role phase uses 1.
        call_kwargs = mock_converse.call_args
        tools_arg = call_kwargs[0][2] if call_kwargs[0] else call_kwargs[1].get("tool_specs", [])
        self.assertEqual(len(tools_arg), 2, "Submission phase must use 2 tool specs")
        self.assertIn("reply", result)

    def test_no_template_routes_to_role_phase(self):
        """When no selected_template, handle_agent_message routes to role phase (1 tool)."""
        with patch("src.agent.index.converse_with_tools") as mock_converse:
            mock_converse.return_value = _end_turn_response(
                "Could you tell me more about your role?"
            )
            result = handle_agent_message(
                "I am a backend developer",
                _SESSION_WITHOUT_TEMPLATE,
                [],
            )

        mock_converse.assert_called_once()
        call_kwargs = mock_converse.call_args
        tools_arg = call_kwargs[0][2] if call_kwargs[0] else call_kwargs[1].get("tool_specs", [])
        self.assertEqual(len(tools_arg), 1, "Role phase must use 1 tool spec (query_db only)")
        self.assertIn("reply", result)


# ---------------------------------------------------------------------------
# Submission detection tests
# ---------------------------------------------------------------------------

class TestSubmissionDetection(unittest.TestCase):

    def _mock_execute_db_success(self, sql: str) -> str:
        return json.dumps({"rows_affected": 1, "success": True})

    def test_execute_db_on_access_requests_returns_request_id(self):
        """
        When Bedrock calls execute_db with access_requests INSERT containing the
        pre-generated request_id, session_update must include request_id.
        """
        captured_request_id: list[str] = []

        def side_effect(system_prompt, messages, tool_specs, max_tokens=768):
            # First call: Bedrock returns tool_use (execute_db)
            if len(captured_request_id) == 0:
                # Extract request_id from system prompt
                import re
                m = re.search(r"VALUES \('([0-9a-f-]+)'", system_prompt)
                rid = m.group(1) if m else "unknown"
                captured_request_id.append(rid)
                sql = (
                    "INSERT INTO access_requests "
                    "(id, acf2_id, designation_id, final_bundle, status, created_at) "
                    f"VALUES ('{rid}', 'ARUN01', 'devops_cloud_engineer', "
                    "'[\"github_repo_access\",\"jira_project_access\"]', 'pending', 1700000000)"
                )
                return _tool_use_response("execute_db", {"sql": sql}, "tu-exec-001")
            # Second call: end_turn after tool result
            return _end_turn_response(
                "Your request has been submitted. Approvals will be routed shortly."
            )

        with patch("src.agent.index.converse_with_tools", side_effect=side_effect):
            with patch(
                "src.agent.index._mcp_execute_db",
                side_effect=self._mock_execute_db_success,
            ):
                result = handle_agent_message(
                    "Yes, submit",
                    _SESSION_WITH_TEMPLATE,
                    [],
                )

        self.assertIn("session_update", result, "session_update must be present after submission")
        su = result["session_update"]
        self.assertIn("request_id", su)
        self.assertIsNotNone(su["request_id"])
        self.assertIn("final_bundle", su)

    def test_execute_db_on_other_table_does_not_set_request_id(self):
        """
        execute_db on a non-access_requests table must not trigger session_update.
        """
        call_count = [0]

        def side_effect(system_prompt, messages, tool_specs, max_tokens=768):
            call_count[0] += 1
            if call_count[0] == 1:
                # Bedrock writes to a different table by mistake
                sql = (
                    "INSERT INTO audit_log (id, acf2_id, event_type, details, created_at) "
                    "VALUES ('log-1', 'ARUN01', 'test', 'test', 1700000000)"
                )
                return _tool_use_response("execute_db", {"sql": sql}, "tu-log-001")
            return _end_turn_response("Done.")

        with patch("src.agent.index.converse_with_tools", side_effect=side_effect):
            with patch(
                "src.agent.index._mcp_execute_db",
                return_value=json.dumps({"rows_affected": 1, "success": True}),
            ):
                result = handle_agent_message(
                    "Submit my request",
                    _SESSION_WITH_TEMPLATE,
                    [],
                )

        self.assertNotIn("session_update", result)

    def test_bedrock_failure_during_submission_returns_fallback(self):
        """Bedrock exception during submission phase returns FALLBACK_REPLY."""
        from src.agent.index import FALLBACK_REPLY

        with patch(
            "src.agent.index.converse_with_tools",
            side_effect=RuntimeError("service unavailable"),
        ):
            result = handle_agent_message(
                "Submit my request",
                _SESSION_WITH_TEMPLATE,
                [],
            )

        self.assertIn("Bedrock is currently unavailable", result["reply"])
        self.assertNotIn("session_update", result)


# ---------------------------------------------------------------------------
# Submission prompt content tests
# ---------------------------------------------------------------------------

class TestSubmissionPromptContent(unittest.TestCase):

    def test_submission_prompt_contains_mandatory_items(self):
        """_build_submission_prompt must list mandatory access item names."""
        from src.agent.index import _build_submission_prompt

        prompt = _build_submission_prompt(
            _SESSION_WITH_TEMPLATE, "req-test-uuid", 1700000000
        )
        self.assertIn("GitHub repository access", prompt)
        self.assertIn("Jira project access", prompt)

    def test_submission_prompt_contains_optional_items(self):
        """_build_submission_prompt must list optional access item names."""
        from src.agent.index import _build_submission_prompt

        prompt = _build_submission_prompt(
            _SESSION_WITH_TEMPLATE, "req-test-uuid", 1700000000
        )
        self.assertIn("PagerDuty", prompt)

    def test_submission_prompt_contains_request_id(self):
        """_build_submission_prompt must embed the pre-generated request_id."""
        from src.agent.index import _build_submission_prompt

        rid = "00000000-0000-0000-0000-000000000042"
        prompt = _build_submission_prompt(_SESSION_WITH_TEMPLATE, rid, 1700000000)
        self.assertIn(rid, prompt)

    def test_submission_prompt_no_internal_ids_instructed_to_user(self):
        """Prompt must instruct agent never to reveal internal IDs to user."""
        from src.agent.index import _build_submission_prompt

        prompt = _build_submission_prompt(
            _SESSION_WITH_TEMPLATE, "req-test-uuid", 1700000000
        )
        self.assertIn("Do not reveal the request ID", prompt)


if __name__ == "__main__":
    unittest.main()
