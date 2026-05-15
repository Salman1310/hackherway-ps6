"""
Jira MCP Server — HackHERway PS6

Exposes Jira Cloud as MCP tools for the access agent.
Creates tickets and queries status via Jira REST API v3.

Tools exposed:
  create_jira_ticket(summary, description, labels) — Create issue in HACK project
  get_jira_status(ticket_key) — Get current status of a Jira issue
  get_jira_tickets_for_request(request_id) — Get all tickets for an access request

Run (from backend/ folder):
    python -m mcp_server.jira_server
"""

import json
import os
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ModuleNotFoundError:
    pass

JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "HACK")


def _auth():
    return (JIRA_EMAIL, JIRA_API_TOKEN)


def _api_url(path: str) -> str:
    return f"{JIRA_BASE_URL}/rest/api/3{path}"


def _is_configured() -> bool:
    return bool(JIRA_BASE_URL and JIRA_EMAIL and JIRA_API_TOKEN)


def create_jira_ticket(
    summary: str,
    description: str,
    labels: list[str] | None = None,
) -> str:
    """
    Create a Jira issue in the configured project.

    Args:
        summary: Issue title (e.g., "[Access Request] Arun Mehta — Confluence")
        description: Plain text description with context
        labels: List of labels to attach (e.g., ["ACF2_ARUN01", "event_uuid"])

    Returns:
        JSON with {"key": "HACK-1", "id": "10036", "url": "..."} on success.
        Returns {"error": "..."} on failure.
    """
    if not _is_configured():
        return json.dumps({"error": "Jira not configured. Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN in .env"})

    safe_labels = [lbl.replace(":", "_").replace(" ", "_") for lbl in (labels or [])]

    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description}]
                }]
            },
            "issuetype": {"name": "Task"},
            "labels": safe_labels,
        }
    }

    try:
        resp = requests.post(
            _api_url("/issue"),
            json=payload,
            auth=_auth(),
            headers={"Content-Type": "application/json"},
            timeout=15,
            verify=False,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            return json.dumps({
                "key": data.get("key", ""),
                "id": data.get("id", ""),
                "url": f"{JIRA_BASE_URL}/browse/{data.get('key', '')}",
                "success": True,
            })
        else:
            return json.dumps({
                "error": f"Jira API returned {resp.status_code}: {resp.text[:200]}"
            })
    except Exception as exc:
        return json.dumps({"error": f"Jira request failed: {str(exc)}"})


def get_jira_status(ticket_key: str) -> str:
    """
    Get the current status of a Jira issue.

    Args:
        ticket_key: The Jira issue key (e.g., "HACK-1")

    Returns:
        JSON with {"key", "status", "assignee", "updated"} on success.
        Returns {"error": "..."} on failure.
    """
    if not _is_configured():
        return json.dumps({"error": "Jira not configured"})

    try:
        resp = requests.get(
            _api_url(f"/issue/{ticket_key}"),
            auth=_auth(),
            params={"fields": "status,assignee,updated,summary"},
            timeout=10,
            verify=False,
        )

        if resp.status_code == 200:
            data = resp.json()
            fields = data.get("fields", {})
            status = fields.get("status", {}).get("name", "Unknown")
            assignee = fields.get("assignee", {})
            assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"

            return json.dumps({
                "key": ticket_key,
                "status": status,
                "assignee": assignee_name,
                "updated": fields.get("updated", ""),
                "summary": fields.get("summary", ""),
            })
        elif resp.status_code == 404:
            return json.dumps({"error": f"Ticket {ticket_key} not found"})
        else:
            return json.dumps({"error": f"Jira API returned {resp.status_code}"})
    except Exception as exc:
        return json.dumps({"error": f"Jira request failed: {str(exc)}"})


def get_jira_tickets_for_request(request_id: str) -> str:
    """
    Search for all Jira tickets linked to an access request.

    Args:
        request_id: The access request UUID

    Returns:
        JSON array of tickets with their status.
    """
    if not _is_configured():
        return json.dumps({"error": "Jira not configured"})

    jql = f'project = {JIRA_PROJECT_KEY} AND labels = "req_{request_id[:8]}"'

    try:
        resp = requests.get(
            _api_url("/search"),
            auth=_auth(),
            params={"jql": jql, "fields": "status,summary,assignee,labels"},
            timeout=10,
            verify=False,
        )

        if resp.status_code == 200:
            data = resp.json()
            tickets = []
            for issue in data.get("issues", []):
                fields = issue.get("fields", {})
                status = fields.get("status", {}).get("name", "Unknown")
                assignee = fields.get("assignee", {})
                tickets.append({
                    "key": issue.get("key", ""),
                    "summary": fields.get("summary", ""),
                    "status": status,
                    "assignee": assignee.get("displayName", "Unassigned") if assignee else "Unassigned",
                    "labels": fields.get("labels", []),
                })
            return json.dumps(tickets)
        else:
            return json.dumps({"error": f"Jira search returned {resp.status_code}"})
    except Exception as exc:
        return json.dumps({"error": f"Jira search failed: {str(exc)}"})
