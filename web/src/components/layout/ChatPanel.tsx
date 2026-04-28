'use client';

import { useEffect, useRef } from 'react';
import { Menu } from 'lucide-react';
import { useSession } from '@/contexts/SessionContext';
import MessageBubble from '@/components/chat/MessageBubble';
import ChatInput from '@/components/chat/ChatInput';

export default function ChatPanel({ onMenuClick }: { onMenuClick: () => void }) {
  const { messages } = useSession();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl overflow-hidden shadow-xl">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100 flex-shrink-0">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <Menu className="w-5 h-5 text-gray-500" />
        </button>
        <div className="w-7 h-7 rounded-full bg-sl-gold flex items-center justify-center flex-shrink-0">
          <HeaderSunIcon />
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="font-semibold text-gray-900 text-sm leading-tight">Access Request</h1>
          <p className="text-[10px] text-gray-400 leading-tight">Powered by AI · Secure · Auditable</p>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          <span className="text-[10px] text-gray-400 font-medium">Live</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-5 chat-scrollbar">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0">
        <ChatInput />
      </div>
    </div>
  );
}

function HeaderSunIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeWidth="2.5">
      <circle cx="12" cy="12" r="4" fill="#1E1E2E" stroke="#1E1E2E" />
      <line x1="12" y1="2" x2="12" y2="5" stroke="#1E1E2E" />
      <line x1="12" y1="19" x2="12" y2="22" stroke="#1E1E2E" />
      <line x1="4.22" y1="4.22" x2="6.34" y2="6.34" stroke="#1E1E2E" />
      <line x1="17.66" y1="17.66" x2="19.78" y2="19.78" stroke="#1E1E2E" />
      <line x1="2" y1="12" x2="5" y2="12" stroke="#1E1E2E" />
      <line x1="19" y1="12" x2="22" y2="12" stroke="#1E1E2E" />
      <line x1="4.22" y1="19.78" x2="6.34" y2="17.66" stroke="#1E1E2E" />
      <line x1="17.66" y1="6.34" x2="19.78" y2="4.22" stroke="#1E1E2E" />
    </svg>
  );
}
