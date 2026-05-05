import os
import boto3
from typing import List, Optional

_client = None

MODEL_ID: str = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6-20250514-v1:0"
)


def get_client():
    global _client
    if _client is None:
        kwargs: dict = {
            "region_name": os.environ.get("AWS_REGION", "us-east-1"),
            "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY"),
        }
        session_token = os.environ.get("AWS_SESSION_TOKEN")
        if session_token:
            kwargs["aws_session_token"] = session_token
        _client = boto3.client("bedrock-runtime", **kwargs)
    return _client


def converse(system_prompt: str, messages: List[dict], max_tokens: int = 512) -> str:
    """
    Simple text-in/text-out Bedrock call (no tools).
    Used by non-agent helpers that need a one-shot LLM response.
    """
    response = get_client().converse(
        modelId=MODEL_ID,
        system=[{"text": system_prompt}],
        messages=messages,
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.7},
    )
    content_blocks = response.get("output", {}).get("message", {}).get("content", [])
    if content_blocks and "text" in content_blocks[0]:
        return content_blocks[0]["text"]
    raise ValueError("No text output from Bedrock")


def converse_with_tools(
    system_prompt: str,
    messages: List[dict],
    tool_specs: List[dict],
    max_tokens: int = 1024,
) -> dict:
    """
    Call Bedrock Converse API with tool definitions.

    Returns the raw response dict from Bedrock. The caller is responsible
    for the tool-use loop — inspecting stopReason, executing tools, and
    appending tool_result messages before calling again.

    Args:
        system_prompt: The system instructions for the model.
        messages:      Conversation history in Bedrock message format.
        tool_specs:    List of tool dicts using Bedrock's toolSpec schema.
        max_tokens:    Maximum tokens for the response.

    Returns:
        Raw Bedrock Converse response dict with keys:
          output.message.content  — list of text / toolUse blocks
          stopReason              — "end_turn" | "tool_use" | "max_tokens"
    """
    return get_client().converse(
        modelId=MODEL_ID,
        system=[{"text": system_prompt}],
        messages=messages,
        toolConfig={"tools": tool_specs},
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.3},
    )
