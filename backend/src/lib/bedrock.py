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
