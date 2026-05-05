'use client';

import {
  createContext,
  useContext,
  useState,
  ReactNode,
  Dispatch,
  SetStateAction,
} from 'react';
import type { SessionState, Message } from '@/lib/types';

const createInitialSession = (): SessionState => ({
  acf2_id: null,
  workday_context: null,
  resolved_role: null,
  selected_template: null,
  final_bundle: [],
  request_id: null,
});

const createWelcomeMessage = (): Message => ({
  id: 'welcome',
  role: 'bot',
  content:
    "Hi! I'm here to help set up your system access. Let's get started - what's your ACF2 ID?",
  timestamp: new Date(),
});

type SessionContextType = {
  session: SessionState;
  setSession: Dispatch<SetStateAction<SessionState>>;
  messages: Message[];
  setMessages: Dispatch<SetStateAction<Message[]>>;
  isLoading: boolean;
  setIsLoading: Dispatch<SetStateAction<boolean>>;
  resetChat: () => void;
};

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionState>(createInitialSession);
  const [messages, setMessages] = useState<Message[]>([createWelcomeMessage()]);
  const [isLoading, setIsLoading] = useState(false);

  function resetChat() {
    setSession(createInitialSession());
    setMessages([createWelcomeMessage()]);
    setIsLoading(false);
  }

  return (
    <SessionContext.Provider
      value={{ session, setSession, messages, setMessages, isLoading, setIsLoading, resetChat }}
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
