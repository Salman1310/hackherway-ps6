import os
from dotenv import load_dotenv

load_dotenv()  # must happen before importing modules that read env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.agent import router as agent_router
from .routes.conversations import router as conversations_router

app = FastAPI(title="HackHERway PS6 — Backend Agent")

# Allow requests from the Next.js frontend on any local network address
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router, prefix="/api/agent")
app.include_router(conversations_router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
