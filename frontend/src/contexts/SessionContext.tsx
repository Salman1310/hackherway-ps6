'use client';

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
  Dispatch,
  SetStateAction,
} from 'react';
import type { AuthUser, SessionState, Message } from '@/lib/types';

const createInitialSession = (): SessionState => ({
  acf2_id: null,
  workday_context: null,
  resolved_role: null,
  selected_template: null,
  final_bundle: [],
  request_id: null,
  agent_trace: null,
});

const createWelcomeMessage = (authUser?: AuthUser | null): Message => ({
  id: 'welcome',
  role: 'bot',
  content: authUser
    ? `Hi ${authUser.name.split(' ')[0]}! I can see you're logged in as ${authUser.acf2_id} (${authUser.team}). Let me check your role and get your access template ready. One moment...`
    : "Hi! I'm here to help set up your system access. Let's get started - what's your ACF2 ID?",
  timestamp: new Date(),
});

type SessionContextType = {
  authUser: AuthUser | null;
  setAuthUser: Dispatch<SetStateAction<AuthUser | null>>;
  authReady: boolean;
  conversationId: string | null;
  setConversationId: Dispatch<SetStateAction<string | null>>;
  session: SessionState;
  setSession: Dispatch<SetStateAction<SessionState>>;
  messages: Message[];
  setMessages: Dispatch<SetStateAction<Message[]>>;
  isLoading: boolean;
  setIsLoading: Dispatch<SetStateAction<boolean>>;
  memoryVersion: number;
  resetChat: () => void;
  deleteMemory: () => Promise<void>;
  logout: () => void;
  loadConversation: (id: string) => Promise<void>;
  restoreLatestConversation: (acf2Id: string) => Promise<void>;
};

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [session, setSession] = useState<SessionState>(createInitialSession);
  const [messages, setMessages] = useState<Message[]>([createWelcomeMessage()]);
  const [isLoading, setIsLoading] = useState(false);
  const [memoryVersion, setMemoryVersion] = useState(0);

  useEffect(() => {
    const raw = window.localStorage.getItem('hackherway.authUser');
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as AuthUser;
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setAuthUser(parsed);
        restoreLatestConversation(parsed.acf2_id);
      } catch {
        window.localStorage.removeItem('hackherway.authUser');
      }
    }
    setAuthReady(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function resetChat() {
    if (authUser) {
      setSession({
        ...createInitialSession(),
        acf2_id: authUser.acf2_id,
        workday_context: {
          name: authUser.name,
          team: authUser.team,
          manager: authUser.manager,
          dept: authUser.dept,
          employment_type: authUser.employment_type,
        },
      });
      setMessages([createWelcomeMessage(authUser)]);
      _autoStartRoleCheck(authUser);
    } else {
      setSession(createInitialSession());
      setMessages([createWelcomeMessage()]);
    }
    setConversationId(null);
    setIsLoading(false);
  }

  async function _autoStartRoleCheck(user: AuthUser) {
    setIsLoading(true);
    try {
      const session: SessionState = {
        ...createInitialSession(),
        acf2_id: user.acf2_id,
        workday_context: {
          name: user.name,
          team: user.team,
          manager: user.manager,
          dept: user.dept,
          employment_type: user.employment_type,
        },
      };
      const res = await fetch('/api/agent/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: `I just logged in. My ACF2 ID is ${user.acf2_id}. Please check my existing role assignment and confirm it with me.`,
          session,
          history: [],
          authenticated_acf2_id: user.acf2_id,
          conversation_id: null,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const botMsg: Message = {
          id: `bot-${Date.now()}`,
          role: 'bot',
          content: data.reply,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, botMsg]);
        if (data.session_update) {
          setSession((prev) => ({ ...prev, ...data.session_update }));
        }
        if (data.conversation_id) {
          setConversationId(data.conversation_id);
        }
      }
    } catch {
      // silent — user can still type manually
    } finally {
      setIsLoading(false);
    }
  }

  async function deleteMemory() {
    if (!authUser?.acf2_id) {
      resetChat();
      return;
    }

    const res = await fetch(
      `/api/conversations?acf2_id=${encodeURIComponent(authUser.acf2_id)}`,
      { method: 'DELETE' },
    );
    if (!res.ok) throw new Error('Unable to delete memory');

    resetChat();
    setMemoryVersion((version) => version + 1);
  }

  function logout() {
    window.localStorage.removeItem('hackherway.authUser');
    setAuthUser(null);
    setSession(createInitialSession());
    setMessages([createWelcomeMessage()]);
    setConversationId(null);
    setIsLoading(false);
  }

  async function restoreLatestConversation(acf2Id: string) {
    try {
      const res = await fetch(`/api/conversations?acf2_id=${encodeURIComponent(acf2Id)}`);
      const data = await res.json();
      const latest = data.conversations?.[0];
      if (latest?.id) {
        await loadConversation(latest.id);
      } else {
        resetChat();
      }
    } catch {
      resetChat();
    }
  }

  async function loadConversation(id: string) {
    const res = await fetch(`/api/conversations/${id}`);
    if (!res.ok) throw new Error('Unable to load conversation');
    const data = await res.json();
    const loadedMessages = (data.messages ?? []).map((m: {
      id: string;
      role: 'bot' | 'user';
      content: string;
      created_at: number;
    }) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      timestamp: new Date(m.created_at * 1000),
    }));

    setConversationId(id);
    setMessages(loadedMessages.length > 0 ? loadedMessages : [createWelcomeMessage()]);
    setSession({ ...createInitialSession(), ...(data.session ?? {}) });
    setIsLoading(false);
  }

  return (
    <SessionContext.Provider
      value={{
        authUser,
        setAuthUser,
        authReady,
        conversationId,
        setConversationId,
        session,
        setSession,
        messages,
        setMessages,
        isLoading,
        setIsLoading,
        memoryVersion,
        resetChat,
        deleteMemory,
        logout,
        loadConversation,
        restoreLatestConversation,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used within SessionProvider');
  return ctx;
}
