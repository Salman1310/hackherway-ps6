'use client';

import { createContext, useContext, useState, ReactNode } from 'react';
import type { SessionState, Message } from '@/lib/types';

const initialSession: SessionState = {
  acf2_id: null,
  workday_context: null,
  resolved_role: null,
  selected_template: null,
  final_bundle: [],
  request_id: null,
};

const welcomeMessage: Message = {
  id: 'welcome',
  role: 'bot',
  content: "Hi! I'm here to help set up your system access. Let's get started. What's your ACF2 ID?",
  timestamp: new Date(),
};

type SessionContextType = {
  session: SessionState;
  setSession: (s: SessionState) => void;
  messages: Message[];
  setMessages: (m: Message[]) => void;
};

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionState>(initialSession);
  const [messages, setMessages] = useState<Message[]>([welcomeMessage]);

  return (
    <SessionContext.Provider value={{ session, setSession, messages, setMessages }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used within SessionProvider');
  return ctx;
}
