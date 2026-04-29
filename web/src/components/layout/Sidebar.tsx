'use client';

import { useEffect, useState } from 'react';
import { Plus, Clock, History, X, MessageSquare } from 'lucide-react';
import { useSession } from '@/contexts/SessionContext';

type Conversation = {
  id: string;
  acf2_id: string;
  created_at: number;
  updated_at: number;
};

export default function Sidebar({ onClose }: { onClose: () => void }) {
  const { session } = useSession();
  const acf2Verified = !!session.acf2_id;

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    if (!session.acf2_id) return;

    setLoadingHistory(true);
    fetch(`/api/conversations?acf2_id=${session.acf2_id}`)
      .then((r) => r.json())
      .then((data) => setConversations(data.conversations ?? []))
      .catch(() => setConversations([]))
      .finally(() => setLoadingHistory(false));
  }, [session.acf2_id]);

  return (
    <div className="flex flex-col h-full bg-sl-dark border-r border-white/10">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-white/10">
        <div className="w-9 h-9 rounded-full bg-sl-gold flex items-center justify-center flex-shrink-0">
          <SunIcon />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-white/50 text-[10px] font-medium uppercase tracking-widest">Sun Life</div>
          <div className="text-white font-bold text-sm leading-tight">Access Assistant</div>
        </div>
        <button
          onClick={onClose}
          className="lg:hidden p-1 rounded-md text-white/40 hover:text-white hover:bg-white/10 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* New Request button */}
      <div className="px-4 py-4">
        <button className="w-full flex items-center justify-center gap-2 bg-sl-gold hover:bg-sl-gold-dark text-sl-dark font-semibold py-2.5 px-4 rounded-lg transition-colors duration-200 text-sm">
          <Plus className="w-4 h-4" strokeWidth={2.5} />
          New Request
        </button>
      </div>

      {/* History */}
      <div className="flex-1 overflow-y-auto px-3 pb-4 thin-scrollbar">
        <div className="flex items-center gap-1.5 text-white/30 text-[10px] font-medium uppercase tracking-widest mb-3 px-1">
          <Clock className="w-3 h-3" />
          Recent Requests
        </div>

        {!acf2Verified ? (
          /* Not verified yet */
          <div className="flex flex-col items-center justify-center gap-3 py-8 px-3 text-center">
            <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center">
              <History className="w-5 h-5 text-white/20" />
            </div>
            <p className="text-white/30 text-xs leading-relaxed">
              Enter your ACF2 ID to load your request history
            </p>
          </div>
        ) : loadingHistory ? (
          /* Fetching */
          <p className="text-white/30 text-xs px-2">Loading history...</p>
        ) : conversations.length === 0 ? (
          /* Verified but no past conversations */
          <div className="flex flex-col items-center justify-center gap-3 py-8 px-3 text-center">
            <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-white/20" />
            </div>
            <p className="text-white/30 text-xs leading-relaxed">
              No previous requests found
            </p>
          </div>
        ) : (
          /* Conversation list */
          <ul className="space-y-1">
            {conversations.map((conv) => (
              <li key={conv.id}>
                <button className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-white/10 transition-colors group">
                  <p className="text-white/70 text-xs font-medium truncate group-hover:text-white transition-colors">
                    Request · {conv.id.slice(0, 8)}
                  </p>
                  <p className="text-white/30 text-[10px] mt-0.5">
                    {new Date(conv.updated_at).toLocaleDateString()}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-white/10">
        <p className="text-white/20 text-[10px] text-center tracking-wide">HackHERway 2025 · PS6</p>
      </div>
    </div>
  );
}

function SunIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeWidth="2.5">
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
