'use client';

import { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { ArrowUp } from 'lucide-react';
import { useSession } from '@/contexts/SessionContext';
import type { Message } from '@/lib/types';

export default function ChatInput() {
  const [value, setValue] = useState('');
  const { messages, setMessages } = useSession();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 128)}px`;
  }, [value]);

  function handleSend() {
    const trimmed = value.trim();
    if (!trimmed) return;
    const msg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    };
    setMessages([...messages, msg]);
    setValue('');
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const canSend = value.trim().length > 0;

  return (
    <div className="px-4 pb-4 pt-2 border-t border-gray-100">
      <div className="flex items-end gap-2 bg-gray-50 rounded-2xl border border-gray-200 px-4 py-2.5 focus-within:border-sl-gold focus-within:ring-2 focus-within:ring-sl-gold/20 transition-all">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          rows={1}
          className="flex-1 bg-transparent text-gray-800 text-sm placeholder-gray-400 resize-none outline-none leading-relaxed"
          style={{ scrollbarWidth: 'none', maxHeight: '128px' }}
        />
        <button
          onClick={handleSend}
          disabled={!canSend}
          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mb-0.5 transition-colors duration-200 bg-sl-dark hover:bg-sl-darker disabled:bg-gray-200 disabled:cursor-not-allowed"
        >
          <ArrowUp className="w-4 h-4 text-white" strokeWidth={2.5} />
        </button>
      </div>
      <p className="text-center text-[10px] text-gray-300 mt-2">
        AI-assisted. All access decisions require manager approval.
      </p>
    </div>
  );
}
