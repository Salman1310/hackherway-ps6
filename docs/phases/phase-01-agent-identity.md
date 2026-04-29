# Phase 01 - Agent Core + Identity Verification

## Status

Current backend-first identity phase. The older UI-shell documentation was replaced because it described the previous frontend-owned business-logic architecture.

## What Was Built

| Deliverable | Location | Purpose |
|---|---|---|
| FastAPI message endpoint | `backend/src/routes/agent.py` | Accepts `POST /api/agent/message` |
| Agent identity flow | `backend/src/agent/index.py` | Extracts or asks for ACF2 ID, verifies user, returns a greeting |
| Bedrock intent parsing | `backend/src/agent/index.py`, `backend/src/lib/bedrock.py` | Uses Claude through Bedrock when available |
| Regex fallback | `backend/src/agent/index.py` | Extracts IDs like `ARUN01` if Bedrock is unavailable |
| SQLite user lookup | `backend/src/lib/sqlite.py` | Reads seeded users from local SQLite |
| Frontend proxy | `frontend/src/app/api/agent/message/route.ts` | Forwards chat messages to FastAPI |
| Chat hook integration | `frontend/src/hooks/useChat.ts` | Sends messages and merges session updates |

## How It Works

```text
User enters message
  -> frontend chat hook
  -> Next.js proxy route
  -> FastAPI /api/agent/message
  -> agent extracts ACF2 ID
  -> backend looks up user
  -> agent returns greeting + session_update
  -> frontend stores ACF2/workday context
```

Unknown IDs return a hard block message and do not update session state.

## How To Test

1. Start the backend:

```bash
cd backend
python scripts/seed_sqlite.py
uvicorn src.main:app --reload --port 8000
```

2. Start the frontend:

```bash
cd frontend
npm run dev
```

3. Open `http://localhost:3000` and test:

| Input | Expected |
|---|---|
| `ARUN01` | Greeting for Arun and session context populated |
| `My ID is NEHA02` | Greeting for Neha and session context populated |
| `FAKE999` | Hard block identity failure message |

## Decisions Made

- The frontend proxy contains no business logic.
- Bedrock failure is not fatal for identity extraction; regex fallback keeps the demo moving.
- Current local seed data uses `ARUN01`, `NEHA02`, and `SARA03`.
