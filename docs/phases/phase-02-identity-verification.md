# Phase 02 — Identity Verification

## Why This Phase Exists

The entire access request flow depends on knowing who is asking. Before any template can be retrieved or any ticket raised, the system must confirm the joinee's identity against an authoritative source.

Phase 2 wires the chat input to a real backend for the first time. The first message a user sends is treated as their ACF2 ID — the system looks it up, confirms them by name in chat, and populates the session. If the ID is unrecognised, the flow stops completely.

## What Was Built

| Deliverable | Location | Purpose |
|---|---|---|
| MongoDB singleton | `web/src/lib/mongodb.ts` | Atlas connection with dev HMR global cache, 5s timeout |
| SQLite singleton | `web/src/lib/sqlite.ts` | Local DB with WAL mode, auto-creates schema on first use |
| Bedrock client | `web/src/lib/bedrock.ts` | `ConverseCommand` wrapper for Claude Sonnet 4.6 |
| Chat hook | `web/src/hooks/useChat.ts` | Sends message → API → updates messages + session |
| Agent message API | `web/src/app/api/agent/message/route.ts` | POST handler: ACF2 lookup → Bedrock greeting → session update |
| Conversations API | `web/src/app/api/conversations/route.ts` | GET handler: returns conversation history by ACF2 ID |
| Typing indicator | `web/src/components/chat/TypingIndicator.tsx` | Animated 3-dot bounce shown while API call is in progress |
| SQLite seed script | `web/scripts/seed-sqlite.mjs` | Upserts 4 demo users, creates all tables, ensures unique index |
| Atlas seed script | `web/scripts/seed.mjs` | Same for MongoDB Atlas (cloud path) |

## Updated Files

| File | What Changed |
|---|---|
| `web/src/contexts/SessionContext.tsx` | Added `isLoading` state + `Dispatch` types for functional updaters |
| `web/src/components/chat/ChatInput.tsx` | Now calls `useChat.sendMessage()` instead of directly updating messages |
| `web/src/components/layout/ChatPanel.tsx` | Renders `<TypingIndicator />` when `isLoading` is true |
| `web/src/components/layout/Sidebar.tsx` | Fetches real history from `/api/conversations`, shows 3-state UI |
| `web/next.config.ts` | Added `serverExternalPackages: ['better-sqlite3']` |
| `web/.env.example` | Added `BEDROCK_MODEL_ID` |
| `web/package.json` | Added `seed` and `seed:sqlite` scripts, `dotenv` dev dependency |
| `web/.gitignore` | Added `*.db`, `*.db-shm`, `*.db-wal` |

## How It Works

### Message Flow

```
User types ACF2 ID → Enter
        │
        ▼
useChat.sendMessage(content)
  1. Adds user message to chat (optimistic)
  2. Sets isLoading = true → TypingIndicator appears
  3. POST /api/agent/message { content, session, history }
        │
        ▼
  API route (route.ts)
  ├── session.acf2_id === null? → handleAcf2Verification(content)
  │     ├── BYPASS_AUTH=true? → lookup mockData directly (instant)
  │     │         OR
  │     ├── Query SQLite: SELECT * FROM users WHERE acf2_id = ?
  │     ├── Not found? → return HARD_BLOCK message
  │     └── Found? → call Bedrock ConverseCommand
  │           ├── Bedrock OK → personalised greeting
  │           └── Bedrock error → hardcoded fallback greeting
  └── session.acf2_id !== null? → Phase 3+ placeholder reply
        │
        ▼
  Returns { reply, session_update? }
        │
        ▼
  useChat receives response
  4. Adds bot reply bubble to chat
  5. Merges session_update into session (acf2_id + workday_context now set)
  6. Sets isLoading = false → TypingIndicator disappears
  7. Sidebar detects acf2_id change → fetches /api/conversations
```

### Stale Closure Prevention

`useChat.ts` captures `snapshot = [...messages, userMsg]` before the `await fetch(...)` call. Bot reply is appended to `snapshot`, not to `messages` from the closure — which may be stale by the time the async call returns.

```typescript
const snapshot = [...messages, userMsg];
setMessages(snapshot);
setIsLoading(true);

const data = await fetch('/api/agent/message', ...).then(r => r.json());

setMessages([...snapshot, botMsg]); // snapshot is captured, not stale
```

### SQLite Schema

```sql
users            — acf2_id (PK), name, team, manager, dept, employment_type
conversations    — id (PK), acf2_id, created_at, updated_at
messages         — id (PK), conversation_id (FK), role, content, created_at
ritm_requests    — id (PK), acf2_id, conversation_id, template_id, status, snow_request_id, created_at
```

`conversations` and `messages` tables are created now and ready for Phase 3+ to write into. Currently empty — sidebar shows "No previous requests found" which is correct.

### Bedrock Integration

```typescript
// bedrock.ts
const command = new ConverseCommand({
  modelId: process.env.BEDROCK_MODEL_ID,
  system: [{ text: systemPrompt }],
  messages: [{ role: 'user', content: [{ text: userPrompt }] }],
  inferenceConfig: { maxTokens: 512, temperature: 0.7 },
});
```

AWS credentials are read from env vars (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`). Session tokens are included when present (required for company-issued temporary credentials).

### Hard Block Behaviour

If ACF2 ID is not found in SQLite (or mock data):
```
"I wasn't able to verify your identity with that ACF2 ID. 
Please double-check and try again, or contact your IT Help Desk if the issue persists."
```
No session update is returned. `session.acf2_id` stays `null`. User must try again.

### Sidebar History

After ACF2 is verified, Sidebar fetches `GET /api/conversations?acf2_id=RIYA001`. Returns list from SQLite `conversations` table ordered by `updated_at DESC`. Three states:

| State | Display |
|-------|---------|
| Not verified | "Enter your ACF2 ID to load your request history" |
| Verified, loading | "Loading history..." (briefly) |
| Verified, no history | "No previous requests found" |
| Verified, has history | Clickable list with dates |

## Key Decisions Made

**SQLite over MongoDB Atlas for local development.**
MongoDB Atlas is blocked by corporate firewall (EACCES on port 27017). SQLite runs locally with zero network dependency, zero config, and sub-millisecond queries. Each machine seeds its own `hackherway.db`. Atlas remains as the cloud production path.

**`BYPASS_AUTH=true` skips database entirely.**
When set, `route.ts` reads directly from `mockData.ts` — no SQLite call, no network call. Useful for rapid testing. When false, SQLite is the authoritative source.

**Bedrock error is never fatal.**
If Bedrock fails (wrong model ID, expired credentials, throttle), the API returns a hardcoded greeting instead of an error. The session is still populated correctly. The flow continues. Demo never crashes on an LLM error.

**MongoDB timeout reduced to 5 seconds.**
Default MongoDB `serverSelectionTimeoutMS` is 30 seconds. Reduced to 5 so the fallback triggers quickly instead of stalling the UI for half a minute.

**Functional updaters on `setSession`.**
`useChat.ts` uses `setSession(prev => ({ ...prev, ...data.session_update }))` instead of `setSession({ ...session, ...data.session_update })`. Prevents stale session state being captured in the async closure.

## Environment Variables Required

| Variable | Required | Notes |
|----------|----------|-------|
| `AWS_ACCESS_KEY_ID` | Yes | From company credentials |
| `AWS_SECRET_ACCESS_KEY` | Yes | From company credentials |
| `AWS_SESSION_TOKEN` | If using temp creds | Company-issued sessions require this |
| `AWS_REGION` | Yes | `us-east-1` |
| `BEDROCK_MODEL_ID` | Yes | Find in AWS Console → Bedrock → Model catalog |
| `BYPASS_AUTH` | Yes | Set `true` for local dev |
| `MONGODB_URI` | No | Only needed if `BYPASS_AUTH=false` and firewall allows Atlas |

## Exit Criteria

| Check | Result |
|---|---|
| Type `RIYA001` → typing indicator appears → personalised greeting returned | PASS |
| Type `FAKE999` → hard block message returned | PASS |
| Session `acf2_id` populated after successful verification | PASS |
| Sidebar switches from empty state to history state after verification | PASS |
| Sidebar shows "No previous requests found" (conversations table empty) | PASS |
| Response time under 5 seconds (BYPASS_AUTH + Bedrock) | PASS |
| No MongoDB connection attempted when `BYPASS_AUTH=true` | PASS |
| TypeScript compiles clean (`npx tsc --noEmit`) | PASS |
