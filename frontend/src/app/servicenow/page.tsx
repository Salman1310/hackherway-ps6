'use client';

import { FormEvent, useEffect, useState } from 'react';

type CatalogItem = {
  id: string;
  display_name: string;
  system: string;
  catalog_id: string;
};

type Ritm = {
  ritm_number: string;
  request_id: string;
  short_description: string;
  role_title: string;
  requested_for: string;
  requested_by: string;
  state: string;
  state_color: string;
  opened_at: number;
  catalog_items: CatalogItem[];
  item_count: number;
};

const STATE_STYLE: Record<string, string> = {
  'Awaiting Approval': 'bg-blue-100 text-blue-800',
  'Closed Complete': 'bg-green-100 text-green-800',
  'Closed Incomplete': 'bg-gray-200 text-gray-700',
};

function formatSnDate(ts: number) {
  return new Date(ts * 1000).toLocaleDateString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }) + ' ' + new Date(ts * 1000).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

// ── Login screen ──────────────────────────────────────────────────────────────

function SnLogin({ onLogin }: { onLogin: (acf2Id: string, name: string) => void }) {
  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acf2_id: userId, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail ?? 'Invalid credentials');
        return;
      }
      onLogin(data.user.acf2_id, data.user.name ?? data.user.acf2_id);
    } catch {
      setError('Unable to reach the server.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f0f0f0] flex flex-col">
      {/* Top bar */}
      <div className="bg-[#293e40] h-10 flex items-center px-6">
        <span className="text-white text-xs font-semibold tracking-wide">ServiceNow</span>
        <span className="text-white/40 text-xs ml-2">| IT Service Management</span>
      </div>

      <div className="flex flex-1 items-center justify-center p-6">
        <div className="bg-white border border-gray-300 w-full max-w-sm shadow-md">
          {/* Header bar */}
          <div className="bg-[#293e40] px-6 py-4">
            <p className="text-white font-semibold text-sm">Employee Self-Service</p>
            <p className="text-white/60 text-xs mt-0.5">Sign in with your employee credentials</p>
          </div>

          <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1 uppercase tracking-wide">
                User ID
              </label>
              <input
                value={userId}
                onChange={(e) => setUserId(e.target.value.toUpperCase())}
                placeholder="ARUN01"
                autoComplete="username"
                className="w-full border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-[#293e40] focus:ring-1 focus:ring-[#293e40]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1 uppercase tracking-wide">
                Password
              </label>
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                placeholder="Demo password"
                autoComplete="current-password"
                className="w-full border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-[#293e40] focus:ring-1 focus:ring-[#293e40]"
              />
            </div>

            {error && (
              <p className="text-xs text-red-700 bg-red-50 border border-red-200 px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading || !userId || !password}
              className="w-full bg-[#293e40] hover:bg-[#1e2e30] disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-sm font-semibold py-2.5 transition-colors"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>

            <p className="text-[11px] text-gray-400 text-center">
              Demo: ARUN01/arun123 · NEHA02/neha123 · SARA03/sara123
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}

// ── RITM detail row ───────────────────────────────────────────────────────────

function RitmRow({ ritm }: { ritm: Ritm }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-300 bg-white mb-2">
      {/* Row */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left px-4 py-3 grid grid-cols-[1fr_auto] gap-4 items-start hover:bg-gray-50 transition-colors"
      >
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm font-bold text-[#293e40] font-mono">{ritm.ritm_number}</span>
            <span
              className={[
                'text-[10px] font-semibold px-2 py-0.5 rounded-sm uppercase tracking-wide',
                STATE_STYLE[ritm.state] ?? 'bg-gray-100 text-gray-600',
              ].join(' ')}
            >
              {ritm.state}
            </span>
          </div>
          <p className="text-xs text-gray-700 mt-1">{ritm.short_description}</p>
          <div className="flex flex-wrap gap-4 mt-1.5 text-[10px] text-gray-500">
            <span>
              <span className="text-gray-400">Role: </span>{ritm.role_title}
            </span>
            <span>
              <span className="text-gray-400">Items: </span>{ritm.item_count}
            </span>
            <span>
              <span className="text-gray-400">Opened: </span>
              {formatSnDate(ritm.opened_at)}
            </span>
            <span>
              <span className="text-gray-400">Requested by: </span>
              {ritm.requested_by}
            </span>
          </div>
        </div>
        <span className="text-gray-400 text-xs mt-1">{expanded ? '▲' : '▼'}</span>
      </button>

      {/* Expanded catalog items */}
      {expanded && (
        <div className="border-t border-gray-200 px-4 py-3">
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Catalog Items
          </p>
          {ritm.catalog_items.length === 0 ? (
            <p className="text-xs text-gray-400">No catalog items found.</p>
          ) : (
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-gray-100">
                  <th className="text-left px-3 py-1.5 font-semibold text-gray-600 border border-gray-200">
                    Item
                  </th>
                  <th className="text-left px-3 py-1.5 font-semibold text-gray-600 border border-gray-200">
                    System
                  </th>
                  <th className="text-left px-3 py-1.5 font-semibold text-gray-600 border border-gray-200">
                    Catalog ID
                  </th>
                </tr>
              </thead>
              <tbody>
                {ritm.catalog_items.map((item) => (
                  <tr key={item.id} className="even:bg-gray-50">
                    <td className="px-3 py-1.5 border border-gray-200 text-gray-800">
                      {item.display_name}
                    </td>
                    <td className="px-3 py-1.5 border border-gray-200 text-gray-600">
                      {item.system || '—'}
                    </td>
                    <td className="px-3 py-1.5 border border-gray-200 font-mono text-gray-500">
                      {item.catalog_id || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main portal ───────────────────────────────────────────────────────────────

export default function ServiceNowPage() {
  const [acf2Id, setAcf2Id] = useState<string | null>(null);
  const [userName, setUserName] = useState('');
  const [ritms, setRitms] = useState<Ritm[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Restore session from sessionStorage (tab-isolated from main app)
  useEffect(() => {
    const raw = window.sessionStorage.getItem('sn.authUser');
    if (raw) {
      try {
        const user = JSON.parse(raw);
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setAcf2Id(user.acf2_id);
        setUserName(user.name ?? user.acf2_id);
      } catch {
        window.sessionStorage.removeItem('sn.authUser');
      }
    }
  }, []);

  useEffect(() => {
    if (!acf2Id) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    fetch(`/api/servicenow/ritms?acf2_id=${encodeURIComponent(acf2Id)}`)
      .then((r) => r.json())
      .then((data) => {
        setRitms(data.ritms ?? []);
        setError(null);
      })
      .catch(() => setError('Failed to load RITM records.'))
      .finally(() => setLoading(false));
  }, [acf2Id]);

  function handleLogin(id: string, name: string) {
    window.sessionStorage.setItem('sn.authUser', JSON.stringify({ acf2_id: id, name }));
    setAcf2Id(id);
    setUserName(name);
  }

  function handleLogout() {
    window.sessionStorage.removeItem('sn.authUser');
    setAcf2Id(null);
    setUserName('');
    setRitms([]);
  }

  if (!acf2Id) return <SnLogin onLogin={handleLogin} />;

  return (
    <div className="min-h-screen bg-[#f0f0f0] flex flex-col text-sm">
      {/* Top navigation bar */}
      <div className="bg-[#293e40] h-10 flex items-center justify-between px-6 flex-shrink-0">
        <div className="flex items-center gap-4">
          <span className="text-white font-bold text-sm tracking-wide">ServiceNow</span>
          <span className="text-white/30 text-xs">|</span>
          <span className="text-white/70 text-xs">IT Service Management</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-white/60 text-xs">{userName}</span>
          <button
            onClick={handleLogout}
            className="text-white/50 hover:text-white text-xs transition-colors"
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Secondary nav */}
      <div className="bg-[#3a5254] px-6 py-1.5 flex items-center gap-6">
        {['Home', 'Self-Service', 'My Requests', 'Knowledge Base'].map((item, i) => (
          <span
            key={item}
            className={[
              'text-xs py-1 cursor-default',
              i === 2
                ? 'text-white border-b-2 border-[#FFD100]'
                : 'text-white/50 hover:text-white/80',
            ].join(' ')}
          >
            {item}
          </span>
        ))}
      </div>

      {/* Page body */}
      <div className="flex-1 p-6">
        <div className="max-w-4xl mx-auto">
          {/* Breadcrumb */}
          <div className="text-[10px] text-gray-500 mb-3">
            Self-Service &rsaquo; My Requests &rsaquo; Request Items
          </div>

          {/* Page header */}
          <div className="bg-white border border-gray-300 px-5 py-3 mb-4 flex items-center justify-between">
            <div>
              <h1 className="text-base font-bold text-gray-800">My Request Items</h1>
              <p className="text-xs text-gray-500 mt-0.5">
                Access requests submitted on behalf of <strong>{userName}</strong>
              </p>
            </div>
            <span className="text-xs text-gray-500 bg-gray-100 border border-gray-200 px-3 py-1">
              {ritms.length} record{ritms.length !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Column headers */}
          {ritms.length > 0 && (
            <div className="grid grid-cols-[150px_1fr_130px_120px] gap-0 bg-gray-200 border border-gray-300 border-b-0 px-4 py-2 text-[10px] font-semibold text-gray-600 uppercase tracking-wider">
              <span>RITM</span>
              <span>Short Description</span>
              <span>State</span>
              <span>Opened</span>
            </div>
          )}

          {/* Records */}
          {loading ? (
            <div className="bg-white border border-gray-300 p-8 text-center text-xs text-gray-400">
              Loading...
            </div>
          ) : error ? (
            <div className="bg-white border border-gray-300 p-8 text-center text-xs text-red-600">
              {error}
            </div>
          ) : ritms.length === 0 ? (
            <div className="bg-white border border-gray-300 p-10 text-center">
              <p className="text-sm text-gray-500 font-medium">No records found</p>
              <p className="text-xs text-gray-400 mt-1">
                Submitted access requests will appear here.
              </p>
            </div>
          ) : (
            <div>
              {ritms.map((ritm) => (
                <RitmRow key={ritm.ritm_number} ritm={ritm} />
              ))}
            </div>
          )}

          {/* Footer */}
          <div className="mt-6 text-[10px] text-gray-400 text-center">
            ServiceNow · IT Service Management Portal · Sun Life Financial
          </div>
        </div>
      </div>
    </div>
  );
}
