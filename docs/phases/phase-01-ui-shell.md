# Phase 01 — UI Shell

## Why This Phase Exists

Before any backend logic is built, the team needs a shared visual target. A working UI shell lets both developers see the full layout, agree on structure, and build backend phases against a real interface rather than an imaginary one.

Phase 1 also de-risks the demo early. The judges' first impression is visual. Locking the layout and Sun Life theming at the start means every subsequent phase adds to a finished-looking product, not a half-rendered skeleton.

## Build Sequence Note

Built before Phase 0. Safe because Phase 1 contains zero backend calls — all content is hardcoded. The UI renders identically whether the database is running or not.

## What Was Built

| Deliverable | Location | Purpose |
|---|---|---|
| 3-panel layout | `web/src/app/page.tsx` | Left sidebar, center chat, right panel — responsive |
| Sidebar | `web/src/components/layout/Sidebar.tsx` | App logo, New Request button, history empty state |
| Chat panel | `web/src/components/layout/ChatPanel.tsx` | Bot/user message bubbles, timestamps, auto-scroll |
| Right panel | `web/src/components/layout/RightPanel.tsx` | Top: template card skeletons. Bottom: approval status tracker |
| Message bubble | `web/src/components/chat/MessageBubble.tsx` | Bot messages left (gray), user messages right (gold) |
| Chat input | `web/src/components/chat/ChatInput.tsx` | Auto-resize textarea, Enter to send, circular send button |
| Session context | `web/src/contexts/SessionContext.tsx` | Global state — session + messages array |
| Type definitions | `web/src/lib/types.ts` | Full TypeScript types matching ADR-002 session shape |
| Sun Life theming | `web/src/app/globals.css` | Tailwind v4 `@theme inline`, gold `#FFD100`, dark `#1E1E2E`, diagonal bg texture |
| App layout | `web/src/app/layout.tsx` | Root layout, `h-full` on html + body |

## How It Works

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  diagonal-bg (#1E1E2E + texture)  h-full overflow-hidden     │
│  ┌─────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │  Sidebar    │  │   ChatPanel      │  │   RightPanel    │ │
│  │  (fixed /   │  │   (flex-1)       │  │   (w-80, lg+)   │ │
│  │  relative)  │  │                  │  │                 │ │
│  └─────────────┘  └──────────────────┘  └─────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

- Sidebar: `fixed` on mobile (slides in/out), `relative` on `lg+` screens
- Right panel: hidden on mobile, visible `lg+` (1024px breakpoint — chosen because company laptop at 1366×768 with 125% scaling has ~1093px effective viewport, below `xl` 1280px breakpoint)
- Chat panel: fills remaining space between sidebar and right panel

### State Management

`SessionContext` provides two pieces of state:
1. `session: SessionState` — ACF2 ID, Workday context, resolved role, template, access bundle, request ID
2. `messages: Message[]` — chat history rendered by `ChatPanel`

Welcome message is hardcoded in context initialisation. Phase 2 appends to `messages` without touching the welcome message.

### Sidebar History Logic

Sidebar uses `session.acf2_id` from context:
- `acf2_id === null` → shows "Enter your ACF2 ID to load your request history"
- `acf2_id !== null` → fetches conversation history from API (wired in Phase 2)

No hardcoded history items. Empty state is the correct state until identity is verified.

### Tailwind v4 Syntax

This project uses Tailwind v4, which has **breaking changes** from v3:

```css
/* globals.css */
@import "tailwindcss";                    /* not @tailwind base/components/utilities */

@theme inline {
  --color-sl-gold: #FFD100;              /* custom tokens via CSS vars, not tailwind.config.js */
  --color-sl-gold-dark: #E6BC00;
  --color-sl-dark: #1E1E2E;
  --color-sl-darker: #16162A;
  --color-sl-surface: #272741;
}
```

Custom classes (`diagonal-bg`, `thin-scrollbar`, `chat-scrollbar`) defined in `globals.css` as regular CSS classes.

## Key Decisions Made

**Sun Life Ask-inspired layout, not a generic chatbot.**
The 3-panel design mirrors Sun Life's internal tooling language. Left sidebar for navigation, center for conversation, right panel for structured data (templates + status). This framing positions the product as enterprise tooling, not a consumer chatbot.

**Hardcoded welcome message committed to source.**
"Hi! I'm here to help set up your system access. Let's get started — what's your ACF2 ID?" is hardcoded in `SessionContext.tsx`. Phase 2 starts responding after that message. No rework required.

**Session state initialised with all nulls, not mocked.**
Avoids hiding Phase 2 bugs behind fake pre-populated state. The empty state forces Phase 2 to correctly populate everything from scratch.

**`suppressHydrationWarning` on timestamp spans.**
`new Date()` in `welcomeMessage` creates a timestamp at module load time on the server. React hydration on the client may see a different minute, causing a mismatch warning. `suppressHydrationWarning` on the timestamp `<span>` suppresses this without hiding real bugs.

**`allowedDevOrigins` in next.config.ts.**
Company laptop accesses dev server via network IP (e.g. `10.158.200.144`) instead of `localhost`. Without this, Next.js blocks HMR WebSocket connections from non-localhost origins.

## Bugs Fixed During This Phase

| Bug | Cause | Fix |
|-----|-------|-----|
| Hydration mismatch on timestamp | `new Date()` called at module load (server time ≠ client time) | `suppressHydrationWarning` on timestamp spans |
| Right panel invisible on company laptop | `xl:flex` breakpoint (1280px) too wide for 1366×768 at 125% DPI | Changed to `lg:flex` (1024px) |
| HMR WebSocket blocked | Next.js rejects cross-origin HMR when accessed via IP | `allowedDevOrigins: ["10.158.200.144"]` in next.config.ts |
| Hardcoded history items always visible | Fake history rendered regardless of ACF2 ID | Replaced with empty state driven by `session.acf2_id` |

## Exit Criteria

| Check | Result |
|---|---|
| Open app → see 3-panel layout (sidebar + chat + right panel) | PASS |
| See hardcoded welcome message in chat | PASS |
| Input field accepts text, Enter sends message | PASS |
| Sending message adds user bubble (no backend response yet) | PASS — expected |
| Sun Life gold theming visible | PASS |
| Sidebar shows empty history state (not hardcoded items) | PASS |
| Right panel visible on company laptop (1366×768 @ 125%) | PASS |
| No React hydration errors in browser console | PASS |
