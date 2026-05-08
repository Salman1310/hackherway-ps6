'use client';

import { FormEvent, useState } from 'react';
import { SessionProvider } from '@/contexts/SessionContext';
import { useSession } from '@/contexts/SessionContext';
import Sidebar from '@/components/layout/Sidebar';
import ChatPanel from '@/components/layout/ChatPanel';
import RightPanel from '@/components/layout/RightPanel';
import type { AuthUser } from '@/lib/types';

export default function Home() {
  return (
    <SessionProvider>
      <LoginGate />
    </SessionProvider>
  );
}

function LoginGate() {
  const { authUser, setAuthUser, authReady, restoreLatestConversation } = useSession();
  const [acf2Id, setAcf2Id] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acf2_id: acf2Id, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail ?? data.error ?? 'Invalid ACF2 ID or password');
        return;
      }
      const user = data.user as AuthUser;
      window.localStorage.setItem('hackherway.authUser', JSON.stringify(user));
      setAuthUser(user);
      await restoreLatestConversation(user.acf2_id);
    } catch {
      setError('Unable to reach the backend. Is it running on port 8000?');
    } finally {
      setSubmitting(false);
    }
  }

  if (!authReady) {
    return <div className="diagonal-bg h-full" />;
  }

  if (!authUser) {
    return (
      <div className="diagonal-bg min-h-full flex items-center justify-center p-4">
        <form
          onSubmit={handleLogin}
          className="w-full max-w-sm bg-white rounded-2xl shadow-xl border border-white/60 p-6"
        >
          <div className="mb-6">
            <div className="w-10 h-10 rounded-full bg-sl-gold flex items-center justify-center mb-4">
              <span className="text-sl-dark font-bold text-lg">S</span>
            </div>
            <h1 className="text-xl font-bold text-gray-900">Access Assistant</h1>
            <p className="text-sm text-gray-500 mt-1">
              Sign in with your demo ACF2 credentials to restore your workspace.
            </p>
          </div>

          <label className="block text-xs font-semibold text-gray-600 mb-1" htmlFor="acf2-id">
            ACF2 ID
          </label>
          <input
            id="acf2-id"
            value={acf2Id}
            onChange={(e) => setAcf2Id(e.target.value.toUpperCase())}
            className="input mb-4"
            placeholder="ARUN01"
            autoComplete="username"
          />

          <label className="block text-xs font-semibold text-gray-600 mb-1" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input mb-4"
            placeholder="Demo password"
            type="password"
            autoComplete="current-password"
          />

          {error && (
            <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2 mb-4">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting || !acf2Id.trim() || !password}
            className="w-full bg-sl-dark hover:bg-sl-darker disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-2.5 px-4 rounded-lg transition-colors text-sm"
          >
            {submitting ? 'Signing in...' : 'Sign In'}
          </button>

          <p className="text-[11px] text-gray-400 mt-4 leading-relaxed">
            Demo users: ARUN01/arun123, NEHA02/neha123, SARA03/sara123.
          </p>
        </form>
      </div>
    );
  }

  return <AuthenticatedApp />;
}

function AuthenticatedApp() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
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
  );
}
