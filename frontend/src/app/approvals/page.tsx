'use client';

import { Suspense, useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  CheckCircle2,
  XCircle,
  Clock,
  User,
  Shield,
  Layers3,
  ArrowLeft,
} from 'lucide-react';
import Link from 'next/link';

type ApprovalEvent = {
  id: string;
  access_request_id: string;
  acf2_id: string;
  role: string;
  team: string;
  access_item: string;
  display_name: string;
  system: string;
  approver: string;
  status: string;
  submitted_at: number;
  resolved_at: number | null;
};

type RequestInfo = {
  id: string;
  acf2_id: string;
  designation_id: string;
  final_bundle: string;
  status: string;
  created_at: number;
};

type ApprovalData = {
  request_id: string;
  request_info: RequestInfo | null;
  events: ApprovalEvent[];
  summary: {
    total: number;
    approved: number;
    rejected: number;
    pending: number;
    overall: string;
  };
};

export default function ApprovalsPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gray-50 flex items-center justify-center"><span className="text-gray-400 text-sm">Loading...</span></div>}>
      <ApprovalsContent />
    </Suspense>
  );
}

function ApprovalsContent() {
  const searchParams = useSearchParams();
  const requestId = searchParams.get('request_id');

  const [data, setData] = useState<ApprovalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!requestId) return;
    try {
      const res = await fetch(`/api/approvals/status/${requestId}`);
      if (!res.ok) throw new Error('Request not found');
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [requestId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleAction = async (eventId: string, action: 'approved' | 'rejected') => {
    setActionInProgress(eventId);
    try {
      const res = await fetch('/api/approvals/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: eventId,
          action,
          approver_name: data?.events.find((e) => e.id === eventId)?.approver || 'Manager',
        }),
      });
      if (res.ok) {
        await fetchStatus();
      }
    } finally {
      setActionInProgress(null);
    }
  };

  const handleApproveAll = async () => {
    if (!data) return;
    const pendingEvents = data.events.filter((e) => e.status === 'pending');
    for (const event of pendingEvents) {
      await handleAction(event.id, 'approved');
    }
  };

  const handleRejectAll = async () => {
    if (!data) return;
    const pendingEvents = data.events.filter((e) => e.status === 'pending');
    for (const event of pendingEvents) {
      await handleAction(event.id, 'rejected');
    }
  };

  if (!requestId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full text-center">
          <Shield className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h1 className="text-lg font-semibold text-gray-800 mb-2">No Request ID</h1>
          <p className="text-sm text-gray-500">
            This page requires a request_id parameter. Use the link from your Teams notification.
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 mt-4 text-sm text-blue-600 hover:text-blue-800"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to main
          </Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-pulse text-gray-400 text-sm">Loading approval details...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full text-center">
          <XCircle className="w-12 h-12 text-red-300 mx-auto mb-4" />
          <h1 className="text-lg font-semibold text-gray-800 mb-2">Request Not Found</h1>
          <p className="text-sm text-gray-500">{error || 'Unable to load approval data.'}</p>
        </div>
      </div>
    );
  }

  const { events, summary, request_info } = data;
  const hasPending = summary.pending > 0;
  const submittedDate = request_info
    ? new Date(request_info.created_at * 1000).toLocaleString()
    : '';

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Link>
          <h1 className="text-xl font-bold text-gray-900">Access Request Approval</h1>
          <p className="text-sm text-gray-500 mt-1">
            Review and approve or reject the access items below.
          </p>
        </div>

        {/* Request summary card */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-4">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center flex-shrink-0">
              <User className="w-5 h-5 text-blue-600" />
            </div>
            <div className="flex-1">
              <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                <div>
                  <span className="text-gray-400 text-xs">Requester</span>
                  <p className="font-medium text-gray-800">{request_info?.acf2_id}</p>
                </div>
                <div>
                  <span className="text-gray-400 text-xs">Role</span>
                  <p className="font-medium text-gray-800">
                    {events[0]?.role || request_info?.designation_id}
                  </p>
                </div>
                <div>
                  <span className="text-gray-400 text-xs">Team</span>
                  <p className="font-medium text-gray-800">{events[0]?.team || '-'}</p>
                </div>
                <div>
                  <span className="text-gray-400 text-xs">Submitted</span>
                  <p className="font-medium text-gray-800">{submittedDate}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Overall status */}
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers3 className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-600">
                  {summary.total} items total
                </span>
              </div>
              <span
                className={[
                  'text-xs font-medium px-2.5 py-1 rounded-full',
                  summary.overall === 'fully_approved'
                    ? 'bg-green-50 text-green-700'
                    : summary.overall === 'partially_rejected'
                    ? 'bg-red-50 text-red-700'
                    : 'bg-amber-50 text-amber-700',
                ].join(' ')}
              >
                {summary.overall === 'fully_approved'
                  ? 'Fully Approved'
                  : summary.overall === 'partially_rejected'
                  ? 'Partially Rejected'
                  : `${summary.pending} pending`}
              </span>
            </div>

            {/* Progress bar */}
            <div className="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden flex">
              {summary.approved > 0 && (
                <div
                  className="h-full bg-green-500 transition-all"
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
            <div className="flex gap-4 mt-2 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500" />
                {summary.approved} approved
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-400" />
                {summary.rejected} rejected
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-gray-300" />
                {summary.pending} pending
              </span>
            </div>
          </div>
        </div>

        {/* Bulk actions */}
        {hasPending && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-4 flex items-center justify-between">
            <p className="text-sm text-gray-600">
              {summary.pending} item{summary.pending !== 1 ? 's' : ''} awaiting your decision
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleApproveAll}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
              >
                <CheckCircle2 className="w-4 h-4" />
                Approve All
              </button>
              <button
                onClick={handleRejectAll}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors"
              >
                <XCircle className="w-4 h-4" />
                Reject All
              </button>
            </div>
          </div>
        )}

        {/* Individual items */}
        <div className="space-y-2">
          {events.map((event) => (
            <div
              key={event.id}
              className={[
                'bg-white rounded-xl shadow-sm border p-4 transition-all',
                event.status === 'approved'
                  ? 'border-green-100'
                  : event.status === 'rejected'
                  ? 'border-red-100'
                  : 'border-gray-100',
              ].join(' ')}
            >
              <div className="flex items-center gap-3">
                {event.status === 'approved' ? (
                  <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0" />
                ) : event.status === 'rejected' ? (
                  <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                ) : (
                  <Clock className="w-5 h-5 text-amber-500 flex-shrink-0" />
                )}

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800">
                    {event.display_name || event.access_item}
                  </p>
                  <p className="text-xs text-gray-500">
                    {event.system && <span>{event.system} · </span>}
                    Approver: {event.approver}
                  </p>
                </div>

                {event.status === 'pending' ? (
                  <div className="flex gap-2 flex-shrink-0">
                    <button
                      onClick={() => handleAction(event.id, 'approved')}
                      disabled={actionInProgress === event.id}
                      className="px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 border border-green-200 rounded-lg transition-colors disabled:opacity-50"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleAction(event.id, 'rejected')}
                      disabled={actionInProgress === event.id}
                      className="px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 rounded-lg transition-colors disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </div>
                ) : (
                  <span
                    className={[
                      'text-xs font-medium px-2 py-1 rounded-full flex-shrink-0',
                      event.status === 'approved'
                        ? 'bg-green-50 text-green-700'
                        : 'bg-red-50 text-red-700',
                    ].join(' ')}
                  >
                    {event.status}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        {!hasPending && summary.total > 0 && (
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-500">
              All items have been reviewed. The requester has been notified.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
