import type { Message } from '@/lib/types';

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function MessageBubble({ message }: { message: Message }) {
  const isBot = message.role === 'bot';

  if (isBot) {
    return (
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-sl-gold flex items-center justify-center flex-shrink-0 shadow-sm mt-0.5">
          <BotIcon />
        </div>
        <div className="flex flex-col gap-1 max-w-[78%]">
          <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-2.5">
            <p className="text-gray-800 text-sm leading-relaxed">{message.content}</p>
          </div>
          <span className="text-[10px] text-gray-400 pl-1">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-end justify-end gap-2">
      <div className="flex flex-col items-end gap-1 max-w-[78%]">
        <div className="bg-sl-gold rounded-2xl rounded-tr-sm px-4 py-2.5">
          <p className="text-sl-dark text-sm leading-relaxed font-medium">{message.content}</p>
        </div>
        <span className="text-[10px] text-gray-400 pr-1">{formatTime(message.timestamp)}</span>
      </div>
    </div>
  );
}

function BotIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeWidth="2.5">
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
