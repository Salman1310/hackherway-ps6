"""
Mock SAM (Software Asset Management) Provisioning API — HackHERway PS6

Endpoints:
    POST /mock/sam/provision/github-copilot
    POST /mock/sam/provision/non-primary-id

Accepts provisioning requests and returns mock success responses.
In production this would call the SAM system API.
"""

import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from ..lib.logger import mock as log_mock

router = APIRouter()


class SAMProvisionRequest(BaseModel):
    acf2_id: str
    access_item: str
    request_id: str | None = None


@router.post("/provision/github-copilot")
def provision_copilot(body: SAMProvisionRequest) -> dict:
    """Mock SAM provisioning for GitHub Copilot license."""
    reference_id = f"SAM-COP-{uuid.uuid4().hex[:8].upper()}"
    log_mock(f"SAM provision Copilot → {body.acf2_id} → {reference_id}")
    return {
        "success": True,
        "system": "SAM",
        "license_type": "github_copilot",
        "acf2_id": body.acf2_id,
        "reference_id": reference_id,
        "message": "GitHub Copilot license assigned",
    }


@router.post("/provision/non-primary-id")
def provision_non_primary(body: SAMProvisionRequest) -> dict:
    """Mock SAM provisioning for non-primary ID / secondary system access."""
    reference_id = f"SAM-NPI-{uuid.uuid4().hex[:8].upper()}"
    log_mock(f"SAM provision non-primary-id → {body.acf2_id} / {body.access_item} → {reference_id}")
    return {
        "success": True,
        "system": "SAM",
        "license_type": "non_primary_id",
        "acf2_id": body.acf2_id,
        "access_item": body.access_item,
        "reference_id": reference_id,
        "message": f"Non-primary ID access provisioned for {body.access_item}",
    }
