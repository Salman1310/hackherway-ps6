import asyncio
import json
import os
import time

from dotenv import load_dotenv

load_dotenv()  # must happen before importing modules that read env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.agent import router as agent_router
from .routes.conversations import router as conversations_router
from .routes.admin import router as admin_router
from .routes.approvals import router as approvals_router
from .routes.auth import router as auth_router
from .routes.servicenow import router as servicenow_router
from .mock.workday import router as workday_router
from .mock.ad import router as ad_router
from .mock.jira import router as jira_router
from .mock.sam import router as sam_router
from .lib.logger import log

app = FastAPI(title="HackHERway PS6 — Backend Agent")

# Allow requests from the Next.js frontend on any local network address
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ────────────────────────────────────────────────────────────────
app.include_router(agent_router,         prefix="/api/agent")
app.include_router(conversations_router, prefix="/api")
app.include_router(admin_router,         prefix="/api/admin")
app.include_router(approvals_router,     prefix="/api/approvals")
app.include_router(auth_router,          prefix="/api/auth")
app.include_router(servicenow_router,    prefix="/api/servicenow")

# ── Mock API routes (Phase 0 — used by Orchestrator in Phase 5) ──────────────
app.include_router(workday_router, prefix="/mock/workday")
app.include_router(ad_router,      prefix="/mock/ad")
app.include_router(jira_router,    prefix="/mock/jira")
app.include_router(sam_router,     prefix="/mock/sam")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
async def startup() -> None:
    log("AGENT", "HackHERway PS6 backend started")
    log("AGENT", "Routes: /api/agent/message, /api/conversations")
    log("MOCK",  "Routes: /mock/workday/employee/{acf2_id}, /mock/ad/provision, /mock/jira/provision, /mock/sam/provision/*")

    # Start Jira status poller if configured
    if os.environ.get("JIRA_BASE_URL"):
        asyncio.create_task(_poll_jira_status())
        log("AGENT", "Jira status poller started (30s interval)")


async def _poll_jira_status() -> None:
    """Poll Jira for status changes on pending tickets and update approvals."""
    from .lib.sqlite import get_db
    from mcp_server.jira_server import get_jira_status

    DONE_STATUSES = {"Done", "Closed", "Resolved", "Approved"}

    while True:
        await asyncio.sleep(30)
        try:
            db = get_db()
            # Find pending approval events that have a jira_ticket_key
            rows = db.execute(
                "SELECT ae.id as event_id, jt.ticket_key "
                "FROM approval_events ae "
                "JOIN jira_tickets jt ON jt.event_id = ae.id "
                "WHERE ae.status = 'pending'"
            ).fetchall()

            for row in rows:
                event_id = row[0]
                ticket_key = row[1]
                result = get_jira_status(ticket_key)
                data = json.loads(result)

                if "error" in data:
                    continue

                status = data.get("status", "")
                if status in DONE_STATUSES:
                    now = int(time.time())
                    approver = data.get("assignee", "Jira Approver")
                    db.execute(
                        "UPDATE approval_events SET status = 'approved', "
                        "approver = ?, resolved_at = ? WHERE id = ?",
                        (approver, now, event_id),
                    )
                    db.commit()
                    log("AGENT", f"Jira approval detected: {ticket_key} -> {event_id} (by {approver})")

                    # Check if all events for this request are resolved
                    req_row = db.execute(
                        "SELECT access_request_id FROM approval_events WHERE id = ?",
                        (event_id,),
                    ).fetchone()
                    if req_row:
                        request_id = req_row[0]
                        all_events = db.execute(
                            "SELECT status FROM approval_events WHERE access_request_id = ?",
                            (request_id,),
                        ).fetchall()
                        if all(e[0] != "pending" for e in all_events):
                            all_approved = all(e[0] == "approved" for e in all_events)
                            new_status = "approved" if all_approved else "partially_rejected"
                            db.execute(
                                "UPDATE access_requests SET status = ? WHERE id = ?",
                                (new_status, request_id),
                            )
                            db.commit()
                            log("AGENT", f"Request {request_id} fully resolved via Jira: {new_status}")

        except Exception as exc:
            log("ERROR", f"Jira poller error: {exc}")
