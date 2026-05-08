'use client';

import { useSession } from '@/contexts/SessionContext';
import type { Message } from '@/lib/types';

export function useChat() {
  const {
    authUser,
    conversationId,
    setConversationId,
    session,
    setSession,
    messages,
    setMessages,
    isLoading,
    setIsLoading,
  } = useSession();

  async function sendMessage(content: string) {
    if (!content.trim() || isLoading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    };

    // Snapshot BEFORE await to avoid stale closure
    const snapshot = [...messages, userMsg];
    setMessages(snapshot);
    setIsLoading(true);

    try {
      const res = await fetch('/api/agent/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: content.trim(),
          session,
          history: messages.map((m) => ({ role: m.role, content: m.content })),
          authenticated_acf2_id: authUser?.acf2_id,
          conversation_id: conversationId,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = (await res.json()) as {
        reply: string;
        session_update?: Partial<typeof session>;
        conversation_id?: string;
      };

      const botMsg: Message = {
        id: `bot-${Date.now()}`,
        role: 'bot',
        content: data.reply,
        timestamp: new Date(),
      };

      setMessages([...snapshot, botMsg]);

      if (data.session_update) {
        setSession((prev) => ({ ...prev, ...data.session_update }));
      }
      if (data.conversation_id) {
        setConversationId(data.conversation_id);
      }
    } catch {
      const errorMsg: Message = {
        id: `err-${Date.now()}`,
        role: 'bot',
        content: "I'm having trouble connecting right now. Please try again in a moment.",
        timestamp: new Date(),
      };
      setMessages([...snapshot, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  }

  return { sendMessage, isLoading };
}
