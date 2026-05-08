import os
from dotenv import load_dotenv

load_dotenv()  # must happen before importing modules that read env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.agent import router as agent_router
from .routes.conversations import router as conversations_router
from .routes.admin import router as admin_router
from .routes.approvals import router as approvals_router
from .routes.auth import router as auth_router
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
