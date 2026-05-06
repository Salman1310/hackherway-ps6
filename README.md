# AI-Powered Access Approval System

**Sun Life HackHERway 2025 - Problem Statement 6**

An AI-powered conversational interface that replaces manual, fragmented access request workflows. The system verifies employee identity, resolves roles, recommends access templates, routes approvals to managers via Microsoft Teams, and maintains a full audit trail.

---

## Demo Flow

```text
Employee opens chat
  -> Provides ACF2 ID (e.g., ARUN01)
  -> AI verifies identity via database lookup
  -> Employee states their role
  -> AI matches a designation template with mandatory/optional access items
  -> Employee reviews and selects optional items in the right panel
  -> Clicks "Submit Request"
  -> Manager receives Teams notification with approval link
  -> Manager opens portal, approves/rejects items
  -> Employee sees real-time status updates
```

---

## Architecture

```text
User
  <-> Next.js frontend (port 3000)
  <-> FastAPI backend (port 8000)
      <-> Conversational Agent
          <-> AWS Bedrock Claude (tool-use loop)
          <-> SQLite MCP server (database queries)
          <-> Mock APIs (Workday, AD, Jira, SAM)
      <-> Approval Engine
          <-> SQLite (approval_events, audit_log)
          <-> MS Teams Incoming Webhook
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4 |
| Backend | Python 3.11+, FastAPI, uvicorn |
| AI/LLM | AWS Bedrock - Claude Opus/Sonnet 4.6 |
| Database | SQLite (local, via MCP tool path) |
| Notifications | MS Teams Incoming Webhook (Adaptive Cards) |
| Mock APIs | Workday, Active Directory, Jira, SAM |

---

## Features

### Phase 1 - Identity Verification
- ACF2 ID lookup against employee database
- Warm greeting with name, team, and manager context
- Hard block on unknown IDs
- Identity lock (one ID per session)

### Phase 2 - Role Resolution & Template Matching
- AI queries normalized designation tables
- Matches role to access template (mandatory + optional items)
- Displays template in right panel grouped by system
- Confidence scoring

### Phase 3 - Access Bundle Submission
- Optional item selection via panel checkboxes
- Bundle summary (mandatory + chosen optional)
- Submission through chat or panel button

### Phase 4 - Admin Portal
- Full CRUD for designations at `/admin/roles`
- Add/edit/delete access items per designation
- Toggle mandatory/optional, set systems and owner teams

### Phase 5 - Approval Workflow & Teams Integration
- Request submission creates per-item approval events
- MS Teams Adaptive Card sent to configured channel
- Manager approval portal at `/approvals?request_id=<id>`
- Bulk approve/reject all or individual items
- Real-time polling (5s) updates requester's panel
- Full audit trail in `audit_log` table

---

## Quick Start

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ LTS |
| Git | Recent |
| AWS credentials | With Bedrock access |

### Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
copy .env.example .env        # then fill in your credentials
python scripts/seed_sqlite.py
uvicorn src.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open http://localhost:3000 in your browser.

---

## Environment Variables

### `backend/.env`

| Variable | Description |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS credentials (or use AWS profile) |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `AWS_SESSION_TOKEN` | Optional session token |
| `AWS_REGION` | AWS region (default: `us-east-1`) |
| `AWS_PROFILE` | AWS profile name (default: `bedrock`) |
| `BEDROCK_MODEL_ID` | Claude model ID |
| `SQLITE_DB_PATH` | Path to SQLite database (default: `./hackherway.db`) |
| `TEAMS_WEBHOOK_URL` | MS Teams Incoming Webhook URL |
| `FRONTEND_PUBLIC_URL` | Frontend URL for Teams card links (default: `http://localhost:3000`) |

### `frontend/.env`

| Variable | Description |
|----------|-------------|
| `BACKEND_URL` | Backend API URL (default: `http://localhost:8000`) |

---

## Demo Users

| ACF2 ID | Name | Team | Scenario |
|---------|------|------|----------|
| `ARUN01` | Arun Mehta | Cloud Infrastructure | Happy path - full flow |
| `NEHA02` | Neha Kapoor | Finance Analytics | Privilege Guard scenario |
| `SARA03` | Sara Chen | TBD | No-match / admin ratification |

---

## API Endpoints

### Agent
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/agent/message` | Send message to conversational agent |

### Conversations
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/conversations` | List conversations |

### Approvals
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/approvals/submit` | Submit request + create approval events + notify Teams |
| GET | `/api/approvals/status/{id}` | Get approval status for a request |
| POST | `/api/approvals/action` | Approve or reject an item |

### Admin
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/designations` | List all designations |
| POST | `/api/admin/designations` | Create a designation |
| PUT | `/api/admin/designations/{id}` | Update a designation |
| DELETE | `/api/admin/designations/{id}` | Delete a designation |
| GET | `/api/admin/designations/{id}/items` | List access items |
| POST | `/api/admin/designations/{id}/items` | Create an access item |
| PUT | `/api/admin/items/{id}` | Update an access item |
| DELETE | `/api/admin/items/{id}` | Delete an access item |

### Mock APIs
| Method | Path | Description |
|--------|------|-------------|
| GET | `/mock/workday/employee/{acf2_id}` | Mock Workday lookup |
| POST | `/mock/ad/provision` | Mock AD provisioning |
| POST | `/mock/jira/provision` | Mock Jira provisioning |
| POST | `/mock/sam/provision/*` | Mock SAM provisioning |

---

## Project Structure

```text
backend/
  src/
    main.py                    # FastAPI app + route registration
    types.py                   # Pydantic models
    agent/index.py             # Conversational agent (Phases 1-3)
    lib/bedrock.py             # AWS Bedrock client
    lib/sqlite.py              # SQLite helpers
    lib/logger.py              # Color-coded logging
    routes/agent.py            # POST /api/agent/message
    routes/conversations.py    # Conversation history
    routes/admin.py            # Admin CRUD routes
    routes/approvals.py        # Approval workflow + Teams webhook
    mock/                      # Mock Workday, AD, Jira, SAM
  mcp_server/sqlite_server.py  # SQLite MCP wrapper
  scripts/seed_sqlite.py       # Database seeding
  requirements.txt

frontend/
  src/
    app/
      page.tsx                 # Main chat page
      admin/roles/page.tsx     # Admin designation manager
      approvals/page.tsx       # Manager approval portal
      api/                     # Next.js proxy routes
    components/
      chat/                    # ChatInput, ChatMessages
      layout/                  # Sidebar, RightPanel
    contexts/SessionContext.tsx # Session state management
    hooks/useChat.ts           # Chat message handling
    lib/types.ts               # TypeScript types

docs/
  phases/                      # Phase documentation
  database_tables_reference.txt

ADR.md                         # Architecture Decision Records
CLAUDE.md                      # AI assistant instructions
PHASES.md                      # Phase tracking
SETUP.md                       # Detailed setup guide
```

---

## Teams Integration Setup

1. Open Microsoft Teams
2. Go to the channel where you want approval notifications
3. Add an **Incoming Webhook** connector (via Workflows or Connectors)
4. Copy the webhook URL
5. Add it to `backend/.env` as `TEAMS_WEBHOOK_URL`
6. Restart the backend

When a request is submitted, an Adaptive Card appears in the channel with a "Review & Approve in Portal" button that links to the approval page.

---

## Verification

```bash
# Backend
cd backend
python -m compileall src mcp_server scripts

# Frontend
cd frontend
npm run lint
npm run build
```

---

## Team

Sun Life HackHERway 2025 - PS6 Team
