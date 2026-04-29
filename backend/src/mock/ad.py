"""
Mock AD/LDAP Provisioning API — HackHERway PS6

Endpoint:
    POST /mock/ad/provision

Accepts a provisioning request and returns a mock success response.
In production this would call Active Directory / LDAP APIs.
"""

import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from ..lib.logger import mock as log_mock

router = APIRouter()


class ADProvisionRequest(BaseModel):
    acf2_id: str
    access_item: str
    request_id: str | None = None


@router.post("/provision")
def provision_ad(body: ADProvisionRequest) -> dict:
    """Mock AD/LDAP provisioning — always succeeds for demo."""
    reference_id = f"AD-{uuid.uuid4().hex[:8].upper()}"
    log_mock(f"AD provision → {body.acf2_id} / {body.access_item} → {reference_id}")
    return {
        "success": True,
        "system": "AD/LDAP",
        "acf2_id": body.acf2_id,
        "access_item": body.access_item,
        "reference_id": reference_id,
        "message": f"AD group membership granted for {body.access_item}",
    }
