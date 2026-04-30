import unittest
from unittest.mock import patch

from src.agent.index import ACF2_SYSTEM_PROMPT, handle_agent_message
from src.types import SessionState


class AgentAcf2Tests(unittest.TestCase):
    def test_prompt_routes_acf2_clarification_to_llm_without_db_lookup(self):
        prompt = ACF2_SYSTEM_PROMPT.lower()

        self.assertIn("acf2 clarification", prompt)
        self.assertIn("do not call query_db", prompt)
        self.assertIn("ask for their acf2 id again", prompt)

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


if __name__ == "__main__":
    unittest.main()
