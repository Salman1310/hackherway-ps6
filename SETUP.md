# Project Setup — Company Laptop (From Scratch)

Sun Life HackHERway PS6 · AI-Powered Access Approval Process Optimization

---

## Prerequisites

Install these before anything else.

| Tool | Version | Download |
|------|---------|---------|
| Node.js | 18+ (LTS recommended) | https://nodejs.org |
| Git | Any recent | https://git-scm.com |

Verify after install:
```bash
node -v    # should print v18.x.x or higher
npm -v     # should print 9.x.x or higher
git --version
```

---

## Step 1 — Get GitHub Access

The repo is **private**. You need two things:

### 1a. Collaborator invite
Ask the repo owner (Salman) to add your GitHub username as a collaborator:
- GitHub → `hackherway-ps6` → Settings → Collaborators → Add people
- You will get an email — accept the invite

### 1b. Personal Access Token (PAT)
GitHub password won't work for git clone. You need a PAT.

1. GitHub → top-right avatar → **Settings**
2. Left sidebar → **Developer settings**
3. **Personal access tokens** → **Tokens (classic)**
4. **Generate new token (classic)**
5. Name it anything (e.g. `hackherway-laptop`)
6. Set expiry: **30 days**
7. Check scope: **repo** (full control of private repositories)
8. Click **Generate token**
9. **Copy it immediately** — you cannot see it again

Save it somewhere safe (e.g. Notepad). You'll paste it as your password when Git asks.

---

## Step 2 — Clone the Repository

Open PowerShell or Command Prompt:

```bash
git clone https://github.com/Salman1310/hackherway-ps6.git
```

When prompted:
```
Username: <your GitHub username>
Password: <paste your PAT here>
```

Then navigate into the project:
```bash
cd hackherway-ps6
```

---

## Step 3 — Install Dependencies

```bash
cd web
npm install
```

This installs all packages including Next.js, SQLite, AWS SDK, etc. Takes ~1–2 minutes first time.

---

## Step 4 — Set Up Environment Variables

```bash
copy .env.example .env
```

Now open `.env` in Notepad (or any text editor) and fill in the values:

```env
# AWS Bedrock — get these from your credentials.txt / AWS console
AWS_ACCESS_KEY_ID=<your key id>
AWS_SECRET_ACCESS_KEY=<your secret key>
AWS_SESSION_TOKEN=<your session token>
AWS_REGION=us-east-1

# Bedrock model — find exact ID in AWS Console → Bedrock → Model catalog
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6-20250514-v1:0

# MongoDB — not required, app uses SQLite locally
MONGODB_URI=mongodb+srv://Hackathon:<password>@hackathon.jjcappv.mongodb.net/hackherway

# ServiceNow — leave blank for now
SERVICENOW_INSTANCE_URL=
SERVICENOW_USERNAME=
SERVICENOW_PASSWORD=

# Teams webhook — leave blank for now
TEAMS_WEBHOOK_URL=
PUBLIC_BASE_URL=http://localhost:3000

# Keep this true — uses local SQLite, skips cloud DB
BYPASS_AUTH=true
```

> **Note:** `.env` is gitignored — it never gets pushed to GitHub. Each person sets it up manually.

---

## Step 5 — Seed the Local Database

This creates `hackherway.db` (SQLite) with 4 demo users. Run once:

```bash
npm run seed:sqlite
```

Expected output:
```
  seeded: RIYA001 — Riya Sharma
  seeded: JOHN002 — John Mathews
  seeded: PRIYA003 — Priya Nair
  seeded: SAM004 — Sam Wilson

Done. DB at: ...\hackherway-ps6\web\hackherway.db
```

---

## Step 6 — Run the App

```bash
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

## Step 7 — Test Identity Verification

Type one of these ACF2 IDs in the chat:

| ACF2 ID | Name | Team |
|---------|------|------|
| `RIYA001` | Riya Sharma | Payments Backend |
| `JOHN002` | John Mathews | Cloud Infrastructure |
| `PRIYA003` | Priya Nair | Finance Analytics |
| `SAM004` | Sam Wilson | TBD |

App should respond with a personalised greeting from Claude (or fallback greeting if Bedrock credentials are not yet configured).

---

## Pulling Updates (After First Setup)

When the repo is updated, run:

```bash
cd hackherway-ps6
git pull origin main
cd web
npm install
npm run dev
```

> Run `npm run seed:sqlite` again only if told to (when the user schema changes).

---

## Troubleshooting

### `npm install` fails with native addon error
Ensure Node.js version is 18+. Run `node -v` to check.

### Git asks for password on every pull
Set up credential storage:
```bash
git config --global credential.helper manager
```
Then pull once and enter your PAT — it will be saved.

### App loads but chat gives no response
Check `.env` — make sure `BYPASS_AUTH=true` is set.

### Bedrock error: invalid model identifier
Open AWS Console → Bedrock → Model catalog → find Claude Sonnet → copy the exact Model ID → update `BEDROCK_MODEL_ID` in `.env` → restart `npm run dev`.

### MongoDB EACCES / ETIMEDOUT errors in console
Expected on company network — corporate firewall blocks Atlas port 27017. App uses SQLite locally and ignores MongoDB errors. Safe to ignore.

### Port 3000 already in use
```bash
npm run dev -- -p 3001
```

---

## Architecture (Quick Reference)

```
Browser → Next.js (localhost:3000)
             │
             ├── /api/agent/message  ← ACF2 lookup (SQLite) + Claude greeting (Bedrock)
             │
             ├── SQLite (hackherway.db)  ← local file, no network needed
             │
             └── AWS Bedrock (Claude Sonnet)  ← via company AWS credentials
```

No MongoDB, no Docker, no additional services needed to run locally.
