'use client';

import { FormEvent, useEffect, useRef, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';

type CatalogItem = {
  id: string;
  display_name: string;
  system: string;
  catalog_id: string;
};

type ApprovalItem = {
  event_id: string;
  access_item: string;
  display_name: string;
  approver: string;
  status: string;
};

type Ritm = {
  ritm_number: string;
  request_id: string;
  short_description: string;
  acf2_id?: string;
  role_title: string;
  requested_for: string;
  requested_by: string;
  state: string;
  state_color: string;
  opened_at: number;
  catalog_items: CatalogItem[];
  approval_items?: ApprovalItem[];
  item_count: number;
  pending_count?: number;
};

type SnUser = {
  acf2_id: string;
  name: string;
  role: 'employee' | 'approver';
};

const STATE_STYLE: Record<string, string> = {
  'Awaiting Approval': 'bg-blue-100 text-blue-800',
  'Closed Complete': 'bg-green-100 text-green-800',
  'Closed Incomplete': 'bg-gray-200 text-gray-700',
};

function formatSnDate(ts: number) {
  return (
    new Date(ts * 1000).toLocaleDateString('en-US', {
      year: 'numeric', month: '2-digit', day: '2-digit',
    }) +
    ' ' +
    new Date(ts * 1000).toLocaleTimeString('en-US', {
      hour: '2-digit', minute: '2-digit', hour12: false,
    })
  );
}

// ── Login ─────────────────────────────────────────────────────────────────────

function SnLogin({ onLogin }: { onLogin: (user: SnUser) => void }) {
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
      if (!res.ok) { setError(data.detail ?? 'Invalid credentials'); return; }
      onLogin({
        acf2_id: data.user.acf2_id,
        name: data.user.name ?? data.user.acf2_id,
        role: data.user.role ?? 'employee',
      });
    } catch {
      setError('Unable to reach the server.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f0f0f0] flex flex-col">
      <div className="bg-[#293e40] h-10 flex items-center px-6">
        <span className="text-white text-xs font-semibold tracking-wide">ServiceNow</span>
        <span className="text-white/40 text-xs ml-2">| IT Service Management</span>
      </div>
      <div className="flex flex-1 items-center justify-center p-6">
        <div className="bg-white border border-gray-300 w-full max-w-sm shadow-md">
          <div className="bg-[#293e40] px-6 py-4">
            <p className="text-white font-semibold text-sm">Employee Self-Service</p>
            <p className="text-white/60 text-xs mt-0.5">Sign in with your employee credentials</p>
          </div>
          <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1 uppercase tracking-wide">User ID</label>
              <input
                value={userId}
                onChange={(e) => setUserId(e.target.value.toUpperCase())}
                placeholder="ARUN01"
                autoComplete="username"
                className="w-full border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-[#293e40] focus:ring-1 focus:ring-[#293e40]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1 uppercase tracking-wide">Password</label>
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
              <p className="text-xs text-red-700 bg-red-50 border border-red-200 px-3 py-2">{error}</p>
            )}
            <button
              type="submit"
              disabled={loading || !userId || !password}
              className="w-full bg-[#293e40] hover:bg-[#1e2e30] disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-sm font-semibold py-2.5 transition-colors"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
            <p className="text-[11px] text-gray-400 text-center">
              Employees: ARUN01 · NEHA02 · SARA03 &nbsp;|&nbsp; Approver: RAJ01/raj123
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}

// ── Employee RITM row (read-only) ─────────────────────────────────────────────

function EmployeeRitmRow({ ritm }: { ritm: Ritm }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border border-gray-300 bg-white mb-2">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left px-4 py-3 grid grid-cols-[1fr_auto] gap-4 items-start hover:bg-gray-50 transition-colors"
      >
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm font-bold text-[#293e40] font-mono">{ritm.ritm_number}</span>
            <span className={['text-[10px] font-semibold px-2 py-0.5 rounded-sm uppercase tracking-wide', STATE_STYLE[ritm.state] ?? 'bg-gray-100 text-gray-600'].join(' ')}>
              {ritm.state}
            </span>
          </div>
          <p className="text-xs text-gray-700 mt-1">{ritm.short_description}</p>
          <div className="flex flex-wrap gap-4 mt-1.5 text-[10px] text-gray-500">
            <span><span className="text-gray-400">Role: </span>{ritm.role_title}</span>
            <span><span className="text-gray-400">Items: </span>{ritm.item_count}</span>
            <span><span className="text-gray-400">Opened: </span>{formatSnDate(ritm.opened_at)}</span>
            <span><span className="text-gray-400">Requested by: </span>{ritm.requested_by}</span>
          </div>
        </div>
        <span className="text-gray-400 text-xs mt-1">{expanded ? '▲' : '▼'}</span>
      </button>
      {expanded && (
        <div className="border-t border-gray-200 px-4 py-3">
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Catalog Items</p>
          {ritm.catalog_items.length === 0 ? (
            <p className="text-xs text-gray-400">No catalog items found.</p>
          ) : (
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-gray-100">
                  <th className="text-left px-3 py-1.5 font-semibold text-gray-600 border border-gray-200">Item</th>
                  <th className="text-left px-3 py-1.5 font-semibold text-gray-600 border border-gray-200">System</th>
                  <th className="text-left px-3 py-1.5 font-semibold text-gray-600 border border-gray-200">Catalog ID</th>
                </tr>
              </thead>
              <tbody>
                {ritm.catalog_items.map((item) => (
                  <tr key={item.id} className="even:bg-gray-50">
                    <td className="px-3 py-1.5 border border-gray-200 text-gray-800">{item.display_name}</td>
                    <td className="px-3 py-1.5 border border-gray-200 text-gray-600">{item.system || '—'}</td>
                    <td className="px-3 py-1.5 border border-gray-200 font-mono text-gray-500">{item.catalog_id || '—'}</td>
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

// ── Approver RITM row (with approve/reject per item) ─────────────────────────

function ApproverRitmRow({
  ritm,
  highlight,
  onActionDone,
}: {
  ritm: Ritm;
  highlight: boolean;
  onActionDone: () => void;
}) {
  const [expanded, setExpanded] = useState(highlight);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const rowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (highlight && rowRef.current) {
      rowRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [highlight]);

  const items = ritm.approval_items ?? [];
  const allResolved = items.every((i) => i.status !== 'pending');

  async function handleAction(eventId: string, action: 'approved' | 'rejected') {
    setActionInProgress(eventId);
    try {
      await fetch('/api/approvals/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_id: eventId, action, approver_name: 'Raj Kumar' }),
      });
      onActionDone();
    } finally {
      setActionInProgress(null);
    }
  }

  async function handleApproveAll() {
    for (const item of items.filter((i) => i.status === 'pending')) {
      await handleAction(item.event_id, 'approved');
    }
  }

  async function handleRejectAll() {
    for (const item of items.filter((i) => i.status === 'pending')) {
      await handleAction(item.event_id, 'rejected');
    }
  }

  return (
    <div
      ref={rowRef}
      className={['border bg-white mb-2 transition-all', highlight ? 'border-blue-400 ring-2 ring-blue-200' : 'border-gray-300'].join(' ')}
    >
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left px-4 py-3 grid grid-cols-[1fr_auto] gap-4 items-start hover:bg-gray-50 transition-colors"
      >
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm font-bold text-[#293e40] font-mono">{ritm.ritm_number}</span>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-sm uppercase tracking-wide bg-blue-100 text-blue-800">
              Awaiting Approval
            </span>
            {highlight && (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-sm bg-amber-100 text-amber-700 uppercase tracking-wide">
                From Teams
              </span>
            )}
          </div>
          <p className="text-xs text-gray-700 mt-1">{ritm.short_description}</p>
          <div className="flex flex-wrap gap-4 mt-1.5 text-[10px] text-gray-500">
            <span><span className="text-gray-400">Role: </span>{ritm.role_title}</span>
            <span><span className="text-gray-400">Items: </span>{ritm.item_count}</span>
            <span><span className="text-gray-400">Opened: </span>{formatSnDate(ritm.opened_at)}</span>
            <span><span className="text-gray-400">Requested for: </span>{ritm.requested_for}</span>
          </div>
        </div>
        <span className="text-gray-400 text-xs mt-1">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="border-t border-gray-200 px-4 py-3">
          {/* Bulk actions */}
          {!allResolved && (
            <div className="flex items-center justify-between mb-3">
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                Approval Items ({items.filter((i) => i.status === 'pending').length} pending)
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleApproveAll}
                  className="px-3 py-1 text-xs font-semibold text-white bg-green-600 hover:bg-green-700 transition-colors rounded-sm"
                >
                  ✓ Approve All
                </button>
                <button
                  onClick={handleRejectAll}
                  className="px-3 py-1 text-xs font-semibold text-white bg-red-500 hover:bg-red-600 transition-colors rounded-sm"
                >
                  ✗ Reject All
                </button>
              </div>
            </div>
          )}
          {allResolved && (
            <p className="text-[10px] font-semibold text-green-700 uppercase tracking-wider mb-3">
              ✓ All items resolved
            </p>
          )}

          {/* Per-item rows */}
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="text-left px-3 py-1.5 font-semibold text-gray-600 border border-gray-200">Item</th>
                <th className="text-left px-3 py-1.5 font-semibold text-gray-600 border border-gray-200">Approver</th>
                <th className="text-left px-3 py-1.5 font-semibold text-gray-600 border border-gray-200">Status</th>
                <th className="text-left px-3 py-1.5 font-semibold text-gray-600 border border-gray-200">Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.event_id} className="even:bg-gray-50">
                  <td className="px-3 py-2 border border-gray-200 text-gray-800">{item.display_name}</td>
                  <td className="px-3 py-2 border border-gray-200 text-gray-600">{item.approver}</td>
                  <td className="px-3 py-2 border border-gray-200">
                    <span className={[
                      'text-[10px] font-semibold px-1.5 py-0.5 rounded-sm uppercase',
                      item.status === 'approved' ? 'bg-green-100 text-green-700'
                        : item.status === 'rejected' ? 'bg-red-100 text-red-600'
                        : 'bg-amber-100 text-amber-700',
                    ].join(' ')}>
                      {item.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 border border-gray-200">
                    {item.status === 'pending' ? (
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => handleAction(item.event_id, 'approved')}
                          disabled={actionInProgress === item.event_id}
                          className="px-2 py-0.5 text-[11px] font-medium text-green-700 bg-green-50 hover:bg-green-100 border border-green-200 rounded-sm disabled:opacity-50 transition-colors"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleAction(item.event_id, 'rejected')}
                          disabled={actionInProgress === item.event_id}
                          className="px-2 py-0.5 text-[11px] font-medium text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 rounded-sm disabled:opacity-50 transition-colors"
                        >
                          Reject
                        </button>
                      </div>
                    ) : (
                      <span className="text-[10px] text-gray-400">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Completed RITM row (read-only, shows resolved items) ─────────────────────

function CompletedRitmRow({ ritm }: { ritm: Ritm }) {
  const [expanded, setExpanded] = useState(false);
  const items = ritm.approval_items ?? [];
  const allApproved = items.every((i) => i.status === 'approved');

  return (
    <div className="border border-gray-300 bg-white mb-2">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left px-4 py-3 grid grid-cols-[1fr_auto] gap-4 items-start hover:bg-gray-50 transition-colors"
      >
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm font-bold text-[#293e40] font-mono">{ritm.ritm_number}</span>
            <span className={['text-[10px] font-semibold px-2 py-0.5 rounded-sm uppercase tracking-wide', allApproved ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-700'].join(' ')}>
              {allApproved ? 'Closed Complete' : 'Closed Incomplete'}
            </span>
          </div>
          <p className="text-xs text-gray-700 mt-1">{ritm.short_description}</p>
          <div className="flex flex-wrap gap-4 mt-1.5 text-[10px] text-gray-500">
            <span><span className="text-gray-400">Role: </span>{ritm.role_title}</span>
            <span><span className="text-gray-400">Items: </span>{ritm.item_count}</span>
            <span><span className="text-gray-400">Opened: </span>{formatSnDate(ritm.opened_at)}</span>
            <span><span className="text-gray-400">Requested for: </span>{ritm.requested_for}</span>
          </div>
        </div>
        <span className="text-gray-400 text-xs mt-1">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="border-t border-gray-200 px-4 py-3">
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Resolution Details</p>
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="text-left px-3 py-1.5 font-semibold text-gray-600 border border-gray-200">Item</th>
                <th className="text-left px-3 py-1.5 font-semibold text-gray-600 border border-gray-200">Approved by</th>
                <th className="text-left px-3 py-1.5 font-semibold text-gray-600 border border-gray-200">Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.event_id} className="even:bg-gray-50">
                  <td className="px-3 py-1.5 border border-gray-200 text-gray-800">{item.display_name}</td>
                  <td className="px-3 py-1.5 border border-gray-200 text-gray-600">{item.approver}</td>
                  <td className="px-3 py-1.5 border border-gray-200">
                    <span className={['text-[10px] font-semibold px-1.5 py-0.5 rounded-sm uppercase', item.status === 'approved' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'].join(' ')}>
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Main portal (inner — uses searchParams) ───────────────────────────────────

function ServiceNowContent() {
  const searchParams = useSearchParams();
  const highlightId = searchParams.get('highlight');

  const [user, setUser] = useState<SnUser | null>(null);
  const [activeTab, setActiveTab] = useState<'pending' | 'completed'>('pending');
  const [pendingRitms, setPendingRitms] = useState<Ritm[]>([]);
  const [completedRitms, setCompletedRitms] = useState<Ritm[]>([]);
  const [employeeRitms, setEmployeeRitms] = useState<Ritm[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Restore session from sessionStorage
  useEffect(() => {
    const raw = window.sessionStorage.getItem('sn.authUser');
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as SnUser;
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setUser(parsed);
      } catch {
        window.sessionStorage.removeItem('sn.authUser');
      }
    }
  }, []);

  const fetchRitms = (currentUser: SnUser) => {
    setLoading(true);
    if (currentUser.role === 'approver') {
      Promise.all([
        fetch('/api/servicenow/pending-ritms').then((r) => r.json()),
        fetch('/api/servicenow/resolved-ritms').then((r) => r.json()),
      ])
        .then(([pending, resolved]) => {
          setPendingRitms(pending.ritms ?? []);
          setCompletedRitms(resolved.ritms ?? []);
          setError(null);
        })
        .catch(() => setError('Failed to load RITM records.'))
        .finally(() => setLoading(false));
    } else {
      fetch(`/api/servicenow/ritms?acf2_id=${encodeURIComponent(currentUser.acf2_id)}`)
        .then((r) => r.json())
        .then((data) => {
          setEmployeeRitms(data.ritms ?? []);
          setError(null);
        })
        .catch(() => setError('Failed to load RITM records.'))
        .finally(() => setLoading(false));
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (user) fetchRitms(user);
  }, [user]);

  function handleLogin(loggedIn: SnUser) {
    window.sessionStorage.setItem('sn.authUser', JSON.stringify(loggedIn));
    setUser(loggedIn);
  }

  function handleLogout() {
    window.sessionStorage.removeItem('sn.authUser');
    setUser(null);
    setPendingRitms([]);
    setCompletedRitms([]);
    setEmployeeRitms([]);
  }

  if (!user) return <SnLogin onLogin={handleLogin} />;

  const isApprover = user.role === 'approver';
  const displayRitms = isApprover
    ? (activeTab === 'pending' ? pendingRitms : completedRitms)
    : employeeRitms;
  const pageTitle = isApprover
    ? (activeTab === 'pending' ? 'Pending Approval Requests' : 'Completed Requests')
    : 'My Request Items';
  const pageSubtitle = isApprover
    ? (activeTab === 'pending'
        ? `${pendingRitms.length} request${pendingRitms.length !== 1 ? 's' : ''} awaiting your approval`
        : `${completedRitms.length} resolved request${completedRitms.length !== 1 ? 's' : ''}`)
    : `Access requests submitted on behalf of ${user.name}`;

  return (
    <div className="min-h-screen bg-[#f0f0f0] flex flex-col text-sm">
      {/* Top bar */}
      <div className="bg-[#293e40] h-10 flex items-center justify-between px-6 flex-shrink-0">
        <div className="flex items-center gap-4">
          <span className="text-white font-bold text-sm tracking-wide">ServiceNow</span>
          <span className="text-white/30 text-xs">|</span>
          <span className="text-white/70 text-xs">IT Service Management</span>
        </div>
        <div className="flex items-center gap-4">
          {isApprover && (
            <span className="text-[10px] font-semibold px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded-sm uppercase tracking-wide">
              Approver
            </span>
          )}
          <span className="text-white/60 text-xs">{user.name}</span>
          <button onClick={handleLogout} className="text-white/50 hover:text-white text-xs transition-colors">
            Sign Out
          </button>
        </div>
      </div>

      {/* Secondary nav */}
      <div className="bg-[#3a5254] px-6 py-1.5 flex items-center gap-6">
        {['Home', 'Self-Service', isApprover ? 'Approvals' : 'My Requests', 'Knowledge Base'].map((item, i) => (
          <span
            key={item}
            className={['text-xs py-1 cursor-default', i === 2 ? 'text-white border-b-2 border-[#FFD100]' : 'text-white/50 hover:text-white/80'].join(' ')}
          >
            {item}
          </span>
        ))}
      </div>

      {/* Body */}
      <div className="flex-1 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-[10px] text-gray-500 mb-3">
            {isApprover ? `Approvals › ${activeTab === 'pending' ? 'Pending' : 'Completed'}` : 'Self-Service › My Requests › Request Items'}
          </div>

          {/* Approver tabs */}
          {isApprover && (
            <div className="flex gap-0 mb-0 border-b border-gray-300">
              <button
                onClick={() => setActiveTab('pending')}
                className={['px-5 py-2 text-xs font-semibold border border-b-0 transition-colors', activeTab === 'pending' ? 'bg-white border-gray-300 text-[#293e40]' : 'bg-gray-100 border-transparent text-gray-500 hover:text-gray-700'].join(' ')}
              >
                Pending
                {pendingRitms.length > 0 && (
                  <span className="ml-1.5 bg-blue-100 text-blue-700 text-[10px] font-bold px-1.5 py-0.5 rounded-sm">
                    {pendingRitms.length}
                  </span>
                )}
              </button>
              <button
                onClick={() => setActiveTab('completed')}
                className={['px-5 py-2 text-xs font-semibold border border-b-0 transition-colors', activeTab === 'completed' ? 'bg-white border-gray-300 text-[#293e40]' : 'bg-gray-100 border-transparent text-gray-500 hover:text-gray-700'].join(' ')}
              >
                Completed
                {completedRitms.length > 0 && (
                  <span className="ml-1.5 bg-green-100 text-green-700 text-[10px] font-bold px-1.5 py-0.5 rounded-sm">
                    {completedRitms.length}
                  </span>
                )}
              </button>
            </div>
          )}

          {/* Page header */}
          <div className="bg-white border border-gray-300 border-t-0 px-5 py-3 mb-4 flex items-center justify-between">
            <div>
              <h1 className="text-base font-bold text-gray-800">{pageTitle}</h1>
              <p className="text-xs text-gray-500 mt-0.5">{pageSubtitle}</p>
            </div>
            <div className="flex items-center gap-3">
              {isApprover && (
                <button
                  onClick={() => fetchRitms(user)}
                  className="text-xs text-[#293e40] hover:underline border border-gray-300 px-3 py-1 bg-gray-50 hover:bg-gray-100 transition-colors"
                >
                  ↻ Refresh
                </button>
              )}
              <span className="text-xs text-gray-500 bg-gray-100 border border-gray-200 px-3 py-1">
                {displayRitms.length} record{displayRitms.length !== 1 ? 's' : ''}
              </span>
            </div>
          </div>

          {/* Column headers */}
          {displayRitms.length > 0 && (
            <div className="grid grid-cols-[150px_1fr_130px_120px] gap-0 bg-gray-200 border border-gray-300 border-b-0 px-4 py-2 text-[10px] font-semibold text-gray-600 uppercase tracking-wider">
              <span>RITM</span>
              <span>Short Description</span>
              <span>State</span>
              <span>Opened</span>
            </div>
          )}

          {/* Records */}
          {loading ? (
            <div className="bg-white border border-gray-300 p-8 text-center text-xs text-gray-400">Loading...</div>
          ) : error ? (
            <div className="bg-white border border-gray-300 p-8 text-center text-xs text-red-600">{error}</div>
          ) : displayRitms.length === 0 ? (
            <div className="bg-white border border-gray-300 p-10 text-center">
              <p className="text-sm text-gray-500 font-medium">
                {isApprover
                  ? (activeTab === 'pending' ? 'No pending requests' : 'No completed requests yet')
                  : 'No records found'}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {isApprover
                  ? (activeTab === 'pending' ? 'All access requests have been resolved.' : 'Approved requests will appear here.')
                  : 'Submitted access requests will appear here.'}
              </p>
            </div>
          ) : (
            <div>
              {isApprover && activeTab === 'pending'
                ? displayRitms.map((ritm) => (
                    <ApproverRitmRow
                      key={ritm.ritm_number}
                      ritm={ritm}
                      highlight={ritm.request_id === highlightId}
                      onActionDone={() => fetchRitms(user)}
                    />
                  ))
                : isApprover && activeTab === 'completed'
                ? displayRitms.map((ritm) => (
                    <CompletedRitmRow key={ritm.ritm_number} ritm={ritm} />
                  ))
                : displayRitms.map((ritm) => (
                    <EmployeeRitmRow key={ritm.ritm_number} ritm={ritm} />
                  ))}
            </div>
          )}

          <div className="mt-6 text-[10px] text-gray-400 text-center">
            ServiceNow · IT Service Management Portal · Sun Life Financial
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Page wrapper (Suspense for useSearchParams) ───────────────────────────────

export default function ServiceNowPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[#f0f0f0] flex items-center justify-center">
        <span className="text-gray-400 text-xs">Loading...</span>
      </div>
    }>
      <ServiceNowContent />
    </Suspense>
  );
}
