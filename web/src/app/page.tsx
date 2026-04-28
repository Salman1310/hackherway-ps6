'use client';

import { useState } from 'react';
import { SessionProvider } from '@/contexts/SessionContext';
import Sidebar from '@/components/layout/Sidebar';
import ChatPanel from '@/components/layout/ChatPanel';
import RightPanel from '@/components/layout/RightPanel';

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <SessionProvider>
      <div className="diagonal-bg flex h-full overflow-hidden">
        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Left sidebar */}
        <aside
          className={[
            'fixed lg:relative inset-y-0 left-0 z-50',
            'w-72 flex-shrink-0',
            'transform transition-transform duration-300 ease-in-out',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
          ].join(' ')}
        >
          <Sidebar onClose={() => setSidebarOpen(false)} />
        </aside>

        {/* Main content */}
        <div className="flex flex-1 min-w-0 p-3 gap-3">
          <main className="flex-1 min-w-0">
            <ChatPanel onMenuClick={() => setSidebarOpen(true)} />
          </main>
          <aside className="hidden lg:flex w-80 flex-shrink-0">
            <RightPanel />
          </aside>
        </div>
      </div>
    </SessionProvider>
  );
}
