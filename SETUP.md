# Project Setup — From Scratch

Sun Life HackHERway PS6 · AI-Powered Access Approval Process Optimization

> **How the project runs:** Two separate processes — a Python backend (port 8000) and a Next.js frontend (port 3000). Both must be running at the same time.

---

## Prerequisites

Install all of these before starting.

| Tool | Version | Download |
|------|---------|---------|
| Python | 3.11+ | https://python.org/downloads |
| Node.js | 18+ LTS | https://nodejs.org |
| Git | Any recent | https://git-scm.com |

Verify after install:
```bash
python --version    # should print Python 3.11.x or higher
node -v             # should print v18.x.x or higher
npm -v
git --version
```

> **Windows note:** If `python` is not found, try `python3`. During Python install, tick **"Add Python to PATH"**.

---

## Step 1 — Get GitHub Access

The repo is **private**. You need two things:

### 1a. Collaborator invite
Ask Salman to add your GitHub username:
- GitHub → `hackherway-ps6` → Settings → Collaborators → Add people
- Accept the email invite

### 1b. Personal Access Token (PAT)
GitHub password won't work for `git clone`. Generate a PAT:

1. GitHub → avatar (top right) → **Settings**
2. Left sidebar → **Developer settings**
3. **Personal access tokens** → **Tokens (classic)**
4. **Generate new token (classic)**
5. Name: `hackherway-laptop` · Expiry: 30 days · Scope: ✅ **repo**
6. Click **Generate token**
7. **Copy immediately** — you cannot see it again

Save it in Notepad. You'll use it as the Git password.

---

## Step 2 — Clone the Repository

```bash
git clone https://github.com/Salman1310/hackherway-ps6.git
cd hackherway-ps6
```

When Git asks:
```
Username: <your GitHub username>
Password: <paste your PAT>
```

Save credentials so Git doesn't ask again:
```bash
git config --global credential.helper manager
```

---

## Step 3 — Backend Setup (Python)

### 3a. Create virtual environment

```bash
cd backend
python -m venv .venv
```

### 3b. Activate virtual environment

```bash
# Windows (PowerShell or Command Prompt)
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate
```

You'll see `(.venv)` at the start of your terminal prompt. **Always activate before running backend commands.**

### 3c. Install Python packages

```bash
pip install -r requirements.txt
```

### 3d. Create backend `.env`

```bash
copy .env.example .env
```

Open `backend/.env` and fill in:

```env
# AWS Bedrock — from your credentials.txt or AWS console
AWS_ACCESS_KEY_ID=<your key id>
AWS_SECRET_ACCESS_KEY=<your secret key>
AWS_SESSION_TOKEN=<your session token>
AWS_REGION=us-east-1

# Find exact model ID: AWS Console → Bedrock → Model catalog → Claude Sonnet
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6-20250514-v1:0

# SQLite — leave as default
SQLITE_DB_PATH=./hackherway.db

# Server port — leave as default
PORT=8000
```

> `.env` is gitignored — never pushed to GitHub. Each person sets it up manually.

### 3e. Seed the database

```bash
python scripts/seed_sqlite.py
```

Expected output:
```
  seeded: RIYA001 — Riya Sharma
  seeded: JOHN002 — John Mathews
  seeded: PRIYA003 — Priya Nair
  seeded: SAM004 — Sam Wilson

Done. DB at: ...\hackherway-ps6\backend\hackherway.db
```

---

## Step 4 — Frontend Setup (Node.js)

Open a **second terminal** (keep the first one for the backend).

```bash
cd hackherway-ps6/frontend
npm install
```

### 4a. Create frontend `.env`

```bash
copy .env.example .env
```

Open `frontend/.env` — it only needs one value:

```env
BACKEND_URL=http://localhost:8000
```

> The frontend has **no AWS credentials**. All AI and database calls go through the backend.

---

## Step 5 — Run the Project

You need **two terminals open at the same time**.

### Terminal 1 — Backend

```bash
cd hackherway-ps6/backend
.venv\Scripts\activate
uvicorn src.main:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Verify it's running: open browser → `http://localhost:8000/health` → should show `{"status":"ok"}`

### Terminal 2 — Frontend

```bash
cd hackherway-ps6/frontend
npm run dev
```

Expected output:
```
▲ Next.js 16.2.4 (Turbopack)
- Local:    http://localhost:3000
- Network:  http://10.x.x.x:3000
✓ Ready in ~2s
```

Open browser → `http://localhost:3000`

---

## Step 6 — Test It Works

Type any of these ACF2 IDs in the chat input:

| ACF2 ID | Name | Team |
|---------|------|------|
| `ARUN01` | Arun Mehta | Cloud Infrastructure |
| `NEHA02` | Neha Kapoor | Finance Analytics |
| `SARA03` | Sara Chen | TBD |

You can also type naturally — e.g. `"My ID is ARUN01"` or `"What's an ACF2 ID?"` — the agent understands natural language.

Expected: typing indicator appears → personalised greeting from Claude.

Type `FAKE999` → hard block message (unknown ID).

---

## Pulling Updates (After First Setup)

When the repo is updated:

```bash
cd hackherway-ps6
git pull origin main
```

Then check if anything new needs to be installed:

```bash
# Backend — only if requirements.txt changed
cd backend
.venv\Scripts\activate
pip install -r requirements.txt

# Frontend — only if package.json changed
cd ../frontend
npm install
```

Run the seed script again only if told to (when the user schema changes).

---

## Architecture (Quick Reference)

```
Browser (port 3000)
    │
    ▼
Next.js Frontend  ← UI only, no AWS credentials
    │  proxies API calls
    ▼
Python Backend (port 8000)
    ├── FastAPI + uvicorn
    ├── Conversational Agent (Bedrock Claude Sonnet)
    │     understands natural language, extracts ACF2 ID,
    │     generates personalised responses
    └── SQLite (hackherway.db)
          local file, no network needed
```

---

## Troubleshooting

### `python` not found
Try `python3` instead. Or reinstall Python and tick **"Add to PATH"** during setup.

### `.venv\Scripts\activate` fails in PowerShell
Run this once to allow scripts:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then activate again.

### Backend starts but chat gives no response
Check that frontend `.env` has `BACKEND_URL=http://localhost:8000` and backend is actually running on port 8000.

### Bedrock error: invalid model identifier
AWS Console → Bedrock → Model catalog → find Claude Sonnet → copy exact Model ID → update `BEDROCK_MODEL_ID` in `backend/.env` → restart backend.

### Bedrock still responds even with wrong credentials
Correct — the agent has a hardcoded fallback greeting. Flow never breaks on Bedrock failure.

### Port 8000 already in use
```bash
uvicorn src.main:app --reload --port 8001
```
Then update `BACKEND_URL=http://localhost:8001` in `frontend/.env`.

### Port 3000 already in use
```bash
npm run dev -- -p 3001
```

### Git asks for password on every pull
```bash
git config --global credential.helper manager
```
Pull once, enter PAT — saved permanently.
