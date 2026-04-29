# Phase 00 — Foundation

## Why This Phase Exists

Every phase from Phase 2 onwards makes real backend calls: database lookups, mock API calls, Bedrock agent invocations. Without a seeded database and running mock APIs, Phase 2 would fail on the first line of code.

Phase 0 is the plumbing. No user-facing features. Pure infrastructure so every subsequent phase has something stable to build on.

## Build Sequence Note

Phase 1 (UI Shell) was built before Phase 0. That was safe because Phase 1 has zero backend calls — it renders hardcoded content only. Phase 0 was completed retroactively before Phase 2 started, which is when the first real backend dependency appears.

## What Was Built

| Deliverable | Location | Purpose |
|---|---|---|
| Folder structure | `agent/`, `mock-apis/`, `schema/`, `orchestrator/` | Establishes repo layout for all future phases |
| Workday mock API | `web/src/app/api/mock/workday/employee/[acf2_id]/route.ts` | Simulates Workday identity lookup |
| SAM mock APIs | `web/src/app/api/mock/sam/provision/...` | Simulates NPE and GitHub Copilot provisioning |
| AD mock API | `web/src/app/api/mock/ad/provision/route.ts` | Simulates Active Directory user creation |
| Jira mock API | `web/src/app/api/mock/jira/provision/route.ts` | Simulates Jira project access provisioning |
| `config.ts` | `web/src/lib/config.ts` | Central env var exports for all API routes |
| `mockData.ts` | `web/src/lib/mockData.ts` | Single source of truth for 4 demo employee records |
| `.env.example` | `web/.env.example` | Documents all required environment variables |
| SQLite DB + schema | `web/src/lib/sqlite.ts` | Local database — users, conversations, messages, ritm_requests tables |
| SQLite seed script | `web/scripts/seed-sqlite.mjs` | Seeds 4 demo users into SQLite via upsert |
| Atlas seed script | `web/scripts/seed.mjs` | Seeds 4 demo users into MongoDB Atlas (cloud path, optional) |
| GitHub repo | `Salman1310/hackherway-ps6` (private) | Remote for collaboration between personal and company laptops |
| `SETUP.md` | repo root | Full onboarding guide for any new machine |

## Architecture Decisions (What Changed from Original Plan)

### MongoDB Atlas M0 instead of Supabase + pgvector
Original plan used Supabase with pgvector for RAG embeddings. Replaced with:
- **MongoDB Atlas M0** (free tier) — cloud document store
- **AWS Bedrock Claude Sonnet 4.6** — replaces Gemini/Ollama as sole LLM provider
- **LLM context stuffing** — all 8 persona templates injected into system prompt, eliminating the need for vector embeddings entirely

### SQLite for local persistence
MongoDB Atlas is blocked by corporate firewall (EACCES on port 27017). Added SQLite (`better-sqlite3`) as a local-first database:
- Runs on every machine with zero network dependency
- `hackherway.db` created locally by `npm run seed:sqlite`
- File is gitignored — each machine has its own copy
- MongoDB Atlas remains as the production/cloud path for when firewall allows

### AWS Bedrock instead of Gemini + Ollama
Company laptops have AWS credentials via `credentials.txt`. All LLM calls go through AWS Bedrock:
- Model: Claude Sonnet 4.6 (`BEDROCK_MODEL_ID` env var)
- Region: `us-east-1`
- Auth: `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` + `AWS_SESSION_TOKEN`

### Mocks as Next.js API routes, not standalone server
Original plan had a separate Express server in `mock-apis/`. Chose Next.js routes instead — single `npm run dev` starts everything, no port management, no separate process.

### `BYPASS_AUTH=true` skips MongoDB entirely
When `BYPASS_AUTH=true` in `.env`, the API route uses mock data directly without attempting any MongoDB connection. No network call, no timeout, instant response.

## Demo Users (Pre-Seeded)

| ACF2 ID | Name | Team | Dept | Type |
|---------|------|------|------|------|
| `RIYA001` | Riya Sharma | Payments Backend | Technology | Full-time |
| `JOHN002` | John Mathews | Cloud Infrastructure | Technology | Full-time |
| `PRIYA003` | Priya Nair | Finance Analytics | Finance | Contract |
| `SAM004` | Sam Wilson | TBD | TBD | Full-time |

## Exit Criteria

| Check | Result |
|---|---|
| `GET /api/mock/workday/employee/RIYA001` → 200 with employee record | PASS |
| `GET /api/mock/workday/employee/FAKE999` → 404 with error | PASS |
| `npm run seed:sqlite` creates `hackherway.db` with 4 users | PASS |
| `npm run build` in `web/` compiles clean (TypeScript strict) | PASS |
| `BYPASS_AUTH=true` → zero MongoDB connection attempts | PASS |
