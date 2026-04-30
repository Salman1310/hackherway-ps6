# Project Setup - From Scratch

Sun Life HackHERway PS6 - AI-Powered Access Approval Process Optimization

The app runs as two local processes:

- Python FastAPI backend on port `8000`
- Next.js frontend on port `3000`

Both must be running for the chat UI to work.

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.11+ | https://python.org/downloads |
| Node.js | 18+ LTS | https://nodejs.org |
| Git | Recent | https://git-scm.com |

Verify:

```bash
python --version
node -v
npm -v
git --version
```

On Windows, if `python` is not found, try `python3` or reinstall Python with "Add Python to PATH" enabled.

---

## Step 1 - Get GitHub Access

The repo is private.

1. Ask Salman to add your GitHub username as a collaborator.
2. Accept the GitHub invite.
3. Create a Personal Access Token with `repo` scope if Git asks for a password.

Clone:

```bash
git clone https://github.com/Salman1310/hackherway-ps6.git
cd hackherway-ps6
```

Optional credential caching:

```bash
git config --global credential.helper manager
```

---

## Step 2 - Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill `backend/.env`:

```env
# AWS Bedrock
AWS_ACCESS_KEY_ID=<your key id>
AWS_SECRET_ACCESS_KEY=<your secret key>
AWS_SESSION_TOKEN=<your session token>
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6-20250514-v1:0

# SQLite
SQLITE_DB_PATH=./hackherway.db

# ServiceNow - Phase 5+
SERVICENOW_INSTANCE_URL=
SERVICENOW_USERNAME=
SERVICENOW_PASSWORD=

# MS Teams - Phase 5+
TEAMS_WEBHOOK_URL=

# Server
PORT=8000
```

`backend/.env` is gitignored. Never commit it.

Seed the database:

```bash
python scripts/seed_sqlite.py
```

Expected output:

```text
  seeded: ARUN01 - Arun Mehta
  seeded: NEHA02 - Neha Kapoor
  seeded: SARA03 - Sara Chen

Done. DB at: ...\hackherway-ps6\backend\hackherway.db
```

---

## Step 3 - Frontend Setup

Open a second terminal:

```bash
cd hackherway-ps6/frontend
npm install
copy .env.example .env
```

Keep only frontend-safe values in `frontend/.env`:

```env
BACKEND_URL=http://localhost:8000
PUBLIC_BASE_URL=http://localhost:3000
```

The frontend must not contain AWS credentials, database credentials, ServiceNow credentials, or `TEAMS_WEBHOOK_URL`.

---

## Step 4 - Run The Project

Terminal 1 - backend:

```bash
cd hackherway-ps6/backend
.venv\Scripts\activate
uvicorn src.main:app --reload --port 8000
```

Verify: open `http://localhost:8000/health`; expected:

```json
{"status":"ok"}
```

Terminal 2 - frontend:

```bash
cd hackherway-ps6/frontend
npm run dev
```

Open `http://localhost:3000`.

You can also run the frontend from the repo root:

```bash
cd hackherway-ps6
npm run dev
```

Do not start Next directly from the repo root with `frontend\node_modules\.bin\next dev`; that makes Tailwind resolve packages from the wrong directory.

---

## Step 5 - Test It Works

Type any of these ACF2 IDs in the chat:

| ACF2 ID | Name | Team | Scenario |
|---------|------|------|----------|
| `ARUN01` | Arun Mehta | Cloud Infrastructure | Happy path + Risk Scorer |
| `NEHA02` | Neha Kapoor | Finance Analytics | Privilege Guard |
| `SARA03` | Sara Chen | TBD | No-match template generation |

Also test natural language:

```text
My ID is ARUN01
```

Expected:

- Known ID: typing indicator appears, then a personalized greeting.
- `FAKE999`: hard-block identity failure message.

---

## Pulling Updates

```bash
cd hackherway-ps6
git pull origin main
```

If backend dependencies changed:

```bash
cd backend
.venv\Scripts\activate
pip install -r requirements.txt
```

If frontend dependencies changed:

```bash
cd frontend
npm install
```

Run the seed script again when schema or demo data changes.

---

## Architecture Quick Reference

```text
Browser on port 3000
  -> Next.js frontend
  -> thin proxy routes
  -> FastAPI backend on port 8000
  -> Python agent and backend services
  -> Bedrock, SQLite MCP, ServiceNow MCP, Teams, mocks
```

Rules:

- Frontend is UI-only.
- Backend owns all AI, database, webhook, and approval logic.
- Secrets live only in `backend/.env`.
- SQLite is local for the hackathon demo.

---

## Troubleshooting

### `python` not found

Try `python3`, or reinstall Python with PATH enabled.

### `.venv\Scripts\activate` fails in PowerShell

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate again.

### Backend starts but chat gives no response

Confirm:

- Backend is running on port `8000`.
- `frontend/.env` has `BACKEND_URL=http://localhost:8000`.
- Frontend was restarted after editing `.env`.

### Bedrock error: invalid model identifier

Copy the exact model ID from AWS Console -> Bedrock -> Model catalog and update `BEDROCK_MODEL_ID` in `backend/.env`.

### Port 8000 already in use

```bash
uvicorn src.main:app --reload --port 8001
```

Then update `BACKEND_URL=http://localhost:8001` in `frontend/.env`.

### Port 3000 already in use

```bash
npm run dev -- -p 3001
```
