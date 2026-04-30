import unittest
from unittest.mock import patch

from src.agent.index import ACF2_SYSTEM_PROMPT, handle_agent_message
from src.types import SessionState


class AgentAcf2Tests(unittest.TestCase):
    def test_prompt_routes_acf2_clarification_to_llm_without_db_lookup(self):
        prompt = ACF2_SYSTEM_PROMPT.lower()

        self.assertIn("acf2 clarification", prompt)
        self.assertIn("do not call query_db", prompt)
        self.assertIn("do not include example ids", prompt)
        self.assertIn("ask for their acf2 id again", prompt)
        acf2_definition = prompt.split("## what is an acf2 id?")[1].split("## how to verify identity")[0]
        self.assertNotIn("arun01", acf2_definition)
        self.assertNotIn("neha02", acf2_definition)

    def test_bedrock_failure_returns_explicit_bedrock_down_message(self):
        with patch(
            "src.agent.index.converse_with_tools",
            side_effect=RuntimeError("network timeout"),
        ):
            result = handle_agent_message(
                "I don't know what is ACF2 ID",
                SessionState(),
                [],
            )

        self.assertIn("Bedrock is currently unavailable", result["reply"])
        self.assertNotIn("session_update", result)

    def test_agent_strips_markdown_bold_from_bedrock_reply(self):
        with patch(
            "src.agent.index.converse_with_tools",
            return_value={
                "stopReason": "end_turn",
                "output": {
                    "message": {
                        "content": [
                            {
                                "text": (
                                    "Your ACF2 ID is **your unique access identifier**. "
                                    "Please enter **your own ID** to continue."
                                )
                            }
                        ]
                    }
                },
            },
        ):
            result = handle_agent_message(
                "What is ACF2 ID?",
                SessionState(),
                [],
            )

        self.assertNotIn("**", result["reply"])
        self.assertIn("your unique access identifier", result["reply"])

    def test_locked_identity_does_not_change_when_user_enters_another_acf2_id(self):
        session = SessionState(
            acf2_id="ARUN01",
            workday_context={
                "name": "Arun Mehta",
                "team": "Cloud Infrastructure",
                "manager": "Raj Kumar",
                "dept": "Technology",
                "employment_type": "full-time",
            },
        )

        with patch("src.agent.index.converse_with_tools") as converse:
            result = handle_agent_message("Actually use NEHA02", session, [])

        converse.assert_not_called()
        self.assertNotIn("session_update", result)
        self.assertIn("already verified as Arun Mehta", result["reply"])
        self.assertIn("reset the chat", result["reply"])
        self.assertNotIn("NEHA02", result["reply"])


if __name__ == "__main__":
    unittest.main()
