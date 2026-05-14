'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  CheckCircle2,
  XCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  ArrowLeft,
  ClipboardList,
  ExternalLink,
} from 'lucide-react';
import Link from 'next/link';

type ApprovalEvent = {
  id: string;
  access_item: string;
  display_name: string;
  system: string;
  approver: string;
  status: string;
  resolved_at: number | null;
};

type RequestSummary = {
  total: number;
  approved: number;
  rejected: number;
  pending: number;
  overall: string;
};

type AccessRequest = {
  id: string;
  acf2_id: string;
  designation_id: string;
  role_title: string;
  status: string;
  created_at: number;
  events: ApprovalEvent[];
  summary: RequestSummary;
};

const OVERALL_LABEL: Record<string, string> = {
  pending: 'Pending',
  pending_approval: 'Pending Approval',
  fully_approved: 'Fully Approved',
  partially_rejected: 'Partially Rejected',
};

const OVERALL_STYLE: Record<string, string> = {
  pending: 'bg-amber-50 text-amber-700 border-amber-200',
  pending_approval: 'bg-blue-50 text-blue-700 border-blue-200',
  fully_approved: 'bg-green-50 text-green-700 border-green-200',
  partially_rejected: 'bg-red-50 text-red-700 border-red-200',
};

function formatDate(ts: number) {
  return new Date(ts * 1000).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function formatTime(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function RequestCard({ request }: { request: AccessRequest }) {
  const [expanded, setExpanded] = useState(false);
  const { summary } = request;
  const overall = summary.overall;
  const hasPending = summary.pending > 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
      {/* Card header — always visible */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left px-5 py-4 flex items-start gap-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-gray-900">{request.role_title}</h3>
            <span
              className={[
                'text-[10px] font-medium px-2 py-0.5 rounded-full border',
                OVERALL_STYLE[overall] ?? 'bg-gray-100 text-gray-500 border-gray-200',
              ].join(' ')}
            >
              {OVERALL_LABEL[overall] ?? overall}
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Submitted {formatDate(request.created_at)} at {formatTime(request.created_at)}
            {' · '}
            <span className="text-gray-500">{summary.total} items</span>
            {summary.approved > 0 && (
              <span className="text-green-600"> · {summary.approved} approved</span>
            )}
            {summary.rejected > 0 && (
              <span className="text-red-500"> · {summary.rejected} rejected</span>
            )}
            {summary.pending > 0 && (
              <span className="text-amber-600"> · {summary.pending} pending</span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0 mt-0.5">
          {hasPending && (
            <Link
              href={`/approvals?request_id=${request.id}`}
              onClick={(e) => e.stopPropagation()}
              className="hidden sm:flex items-center gap-1 text-[11px] font-medium text-blue-600 hover:text-blue-800 border border-blue-200 hover:border-blue-400 bg-blue-50 hover:bg-blue-100 px-2.5 py-1 rounded-lg transition-colors"
            >
              Review
              <ExternalLink className="w-3 h-3" />
            </Link>
          )}
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* Progress bar */}
      {summary.total > 0 && (
        <div className="px-5 pb-3 -mt-1">
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden flex">
            {summary.approved > 0 && (
              <div
                className="h-full bg-green-400 transition-all"
                style={{ width: `${(summary.approved / summary.total) * 100}%` }}
              />
            )}
            {summary.rejected > 0 && (
              <div
                className="h-full bg-red-400 transition-all"
                style={{ width: `${(summary.rejected / summary.total) * 100}%` }}
              />
            )}
          </div>
        </div>
      )}

      {/* Expanded items */}
      {expanded && (
        <div className="border-t border-gray-100 px-5 py-3 space-y-2">
          {request.events.length === 0 ? (
            <p className="text-xs text-gray-400 py-2">No approval events found.</p>
          ) : (
            request.events.map((event) => (
              <div
                key={event.id}
                className={[
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 border',
                  event.status === 'approved'
                    ? 'bg-green-50/60 border-green-100'
                    : event.status === 'rejected'
                    ? 'bg-red-50/60 border-red-100'
                    : 'bg-gray-50 border-gray-100',
                ].join(' ')}
              >
                {event.status === 'approved' ? (
                  <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0" />
                ) : event.status === 'rejected' ? (
                  <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                ) : (
                  <Clock className="w-4 h-4 text-amber-500 flex-shrink-0 animate-pulse" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-800 truncate">
                    {event.display_name || event.access_item}
                  </p>
                  <p className="text-[10px] text-gray-400">
                    {event.system && <span>{event.system} · </span>}
                    {event.approver}
                  </p>
                </div>
                <span
                  className={[
                    'text-[10px] font-medium px-1.5 py-0.5 rounded-full flex-shrink-0 capitalize',
                    event.status === 'approved'
                      ? 'bg-green-100 text-green-700'
                      : event.status === 'rejected'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-amber-100 text-amber-700',
                  ].join(' ')}
                >
                  {event.status}
                </span>
              </div>
            ))
          )}

          {hasPending && (
            <div className="pt-1">
              <Link
                href={`/approvals?request_id=${request.id}`}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-800"
              >
                View in Approval Portal
                <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function MyRequestsPage() {
  const [acf2Id, setAcf2Id] = useState<string | null>(null);
  const [userName, setUserName] = useState<string>('');
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const raw = window.localStorage.getItem('hackherway.authUser');
    if (!raw) {
      window.location.href = '/';
      return;
    }
    try {
      const user = JSON.parse(raw);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAcf2Id(user.acf2_id);
      setUserName(user.name ?? user.acf2_id);
    } catch {
      window.location.href = '/';
    }
  }, []);

  const fetchRequests = useCallback(async () => {
    if (!acf2Id) return;
    try {
      const res = await fetch(`/api/approvals/my-requests?acf2_id=${encodeURIComponent(acf2Id)}`);
      if (!res.ok) throw new Error('Failed to load requests');
      const data = await res.json();
      setRequests(data.requests ?? []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [acf2Id]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (acf2Id) fetchRequests();
  }, [acf2Id, fetchRequests]);

  // Poll every 10s if any request has pending items
  useEffect(() => {
    const hasPending = requests.some((r) => r.summary.pending > 0);
    if (!hasPending) return;
    const interval = setInterval(fetchRequests, 10_000);
    return () => clearInterval(interval);
  }, [requests, fetchRequests]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <Link
          href="/"
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </Link>
        <div className="h-4 w-px bg-gray-200" />
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-slate-800 flex items-center justify-center">
            <ClipboardList className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-gray-900 leading-tight">My Requests</h1>
            {userName && (
              <p className="text-[10px] text-gray-400 leading-tight">{userName}</p>
            )}
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="max-w-2xl mx-auto px-4 py-6">
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
                <div className="h-3.5 bg-gray-100 rounded w-1/3 mb-2" />
                <div className="h-2.5 bg-gray-100 rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="bg-white rounded-xl border border-red-100 p-6 text-center">
            <XCircle className="w-8 h-8 text-red-300 mx-auto mb-2" />
            <p className="text-sm text-gray-600">{error}</p>
          </div>
        ) : requests.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-10 text-center">
            <ClipboardList className="w-10 h-10 text-gray-200 mx-auto mb-3" />
            <p className="text-sm font-medium text-gray-500">No requests yet</p>
            <p className="text-xs text-gray-400 mt-1">
              Access requests you submit will appear here.
            </p>
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 mt-4 text-sm text-blue-600 hover:text-blue-800"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Go to Access Assistant
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {requests.map((req) => (
              <RequestCard key={req.id} request={req} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
