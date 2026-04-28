'use client';

import { Plus, Clock, X } from 'lucide-react';

type HistoryItem = {
  id: string;
  label: string;
  date: string;
  status: 'in-progress' | 'approved' | 'completed';
};

const historyItems: HistoryItem[] = [
  { id: '1', label: 'Backend Developer Setup', date: 'Today', status: 'in-progress' },
  { id: '2', label: 'DevOps Access Request', date: 'Yesterday', status: 'approved' },
  { id: '3', label: 'Data Analyst Onboarding', date: 'Apr 22', status: 'completed' },
];

const statusStyles: Record<HistoryItem['status'], string> = {
  'in-progress': 'text-sl-gold',
  approved: 'text-green-400',
  completed: 'text-white/30',
};

const statusLabels: Record<HistoryItem['status'], string> = {
  'in-progress': 'In Progress',
  approved: 'Approved',
  completed: 'Completed',
};

export default function Sidebar({ onClose }: { onClose: () => void }) {
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
        <div className="flex items-center gap-1.5 text-white/30 text-[10px] font-medium uppercase tracking-widest mb-2 px-1">
          <Clock className="w-3 h-3" />
          Recent Requests
        </div>
        <ul className="space-y-0.5">
          {historyItems.map((item) => (
            <li key={item.id}>
              <button className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-white/5 transition-colors group">
                <div className="text-white/70 text-sm font-medium group-hover:text-white truncate">
                  {item.label}
                </div>
                <div className="flex items-center justify-between mt-0.5">
                  <span className="text-white/30 text-xs">{item.date}</span>
                  <span className={`text-xs ${statusStyles[item.status]}`}>
                    {statusLabels[item.status]}
                  </span>
                </div>
              </button>
            </li>
          ))}
        </ul>
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
