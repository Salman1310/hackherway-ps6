"""
Mock Jira Provisioning API — HackHERway PS6

Endpoint:
    POST /mock/jira/provision

Accepts a provisioning request and returns a mock success response.
In production this would call the Jira REST API.
"""

import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from ..lib.logger import mock as log_mock

router = APIRouter()


class JiraProvisionRequest(BaseModel):
    acf2_id: str
    access_item: str
    project_key: str | None = None
    request_id: str | None = None


@router.post("/provision")
def provision_jira(body: JiraProvisionRequest) -> dict:
    """Mock Jira provisioning — always succeeds for demo."""
    reference_id = f"JIRA-{uuid.uuid4().hex[:8].upper()}"
    log_mock(f"Jira provision → {body.acf2_id} / {body.access_item} → {reference_id}")
    return {
        "success": True,
        "system": "Jira",
        "acf2_id": body.acf2_id,
        "access_item": body.access_item,
        "reference_id": reference_id,
        "message": f"Jira project access granted for {body.access_item}",
    }
