'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  CheckCircle2,
  Circle,
  Layers3,
  User,
  Users,
  Building2,
  ShieldCheck,
  Package,
  Clock,
  Send,
  Loader2,
  XCircle,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useSession } from '@/contexts/SessionContext';
import type { AccessItem, AgentTrace } from '@/lib/types';

const STEPS = [
  { label: 'Request Created', icon: Package },
  { label: 'Manager Approval', icon: Users },
  { label: 'Team Approval', icon: ShieldCheck },
  { label: 'Provisioned', icon: CheckCircle2 },
];

type ApprovalEvent = {
  id: string;
  access_item: string;
  display_name: string;
  system: string;
  approver: string;
  status: string;
  resolved_at: number | null;
};

type ApprovalStatus = {
  events: ApprovalEvent[];
  summary: {
    total: number;
    approved: number;
    rejected: number;
    pending: number;
    overall: string;
  };
};

function AgentReasoningPanel({ trace }: { trace: AgentTrace }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50/60 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-slate-100/60 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">
            Agent Reasoning
          </span>
        </div>
        {open ? (
          <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
        )}
      </button>

      {open && (
        <div className="px-3 pb-3 pt-1 space-y-2">
          {trace.steps.map((step, i) => (
            <div key={i} className="flex items-start gap-2.5">
              {/* Step icon */}
              <div className="mt-0.5 flex-shrink-0">
                {step.status === 'done' ? (
                  <div className="w-4 h-4 rounded-full bg-slate-200 flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                  </div>
                ) : (
                  <div className="w-4 h-4 rounded-full border border-slate-200" />
                )}
              </div>
              {/* Step text */}
              <div className="min-w-0">
                <p className="text-[11px] font-medium text-slate-700 leading-snug">
                  {step.label}
                </p>
                {step.detail && (
                  <p className="text-[10px] text-slate-400 mt-0.5 leading-snug">
                    {step.detail}
                  </p>
                )}
              </div>
            </div>
          ))}
          {/* Confidence footer */}
          <div className="mt-1 pt-2 border-t border-slate-100 flex items-center justify-between">
            <span className="text-[10px] text-slate-400">Match confidence</span>
            <span className="text-[10px] font-semibold text-slate-600">
              {Math.round(trace.confidence * 100)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function RightPanel() {
  const { session, setSession, setMessages } = useSession();
  const template = session.selected_template;
  const resolvedRole = session.resolved_role;
  const workday = session.workday_context;
  const agentTrace = session.agent_trace;
  const hasTemplate = Boolean(template);
  const isSubmitted = Boolean(session.request_id);

  const [submitting, setSubmitting] = useState(false);
  const [approvalStatus, setApprovalStatus] = useState<ApprovalStatus | null>(null);
  const [teamsNotified, setTeamsNotified] = useState(false);

  const bundleIds = session.final_bundle
    .filter((i) => i && i.id)
    .map((i) => i.id);

  const toggleOptionalItem = (item: AccessItem) => {
    if (isSubmitted) return;
    setSession((prev) => {
      const isChecked = prev.final_bundle.some((i) => i.id === item.id);
      const newBundle = isChecked
        ? prev.final_bundle.filter((i) => i.id !== item.id)
        : [...prev.final_bundle, item];
      return { ...prev, final_bundle: newBundle };
    });
  };

  const mandatoryCount = template?.mandatory_access.length ?? 0;
  const selectedOptionalCount = template
    ? template.optional_access.filter((i) => bundleIds.includes(i.id)).length
    : 0;
  const totalSelected = mandatoryCount + selectedOptionalCount;

  // Group items by system
  const groupBySystem = (items: AccessItem[]) => {
    const groups: Record<string, AccessItem[]> = {};
    for (const item of items) {
      const sys = item.system || 'Other';
      if (!groups[sys]) groups[sys] = [];
      groups[sys].push(item);
    }
    return groups;
  };

  // Submit request
  const handleSubmit = async () => {
    if (!template || !session.acf2_id || submitting) return;

    const allItems = [
      ...template.mandatory_access,
      ...template.optional_access.filter((i) => bundleIds.includes(i.id)),
    ];

    setSubmitting(true);
    try {
      const res = await fetch('/api/approvals/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          acf2_id: session.acf2_id,
          designation_id: template.id,
          final_bundle: allItems.map((i) => ({ id: i.id, name: i.name })),
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setSession((prev) => ({ ...prev, request_id: data.request_id }));
        setTeamsNotified(data.teams_notified ?? false);

        const confirmMsg = {
          id: `bot-submit-${Date.now()}`,
          role: 'bot' as const,
          content: `Your access request has been submitted successfully (ID: ${data.request_id.slice(0, 8)}…). ${totalSelected} item${totalSelected !== 1 ? 's' : ''} sent for approval to ${data.manager ?? 'your manager'}.${data.teams_notified ? ' Your manager has been notified via Microsoft Teams.' : ''} I'll keep you updated on the approval progress.`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, confirmMsg]);
      }
    } finally {
      setSubmitting(false);
    }
  };

  // Poll approval status
  const fetchApprovalStatus = useCallback(async () => {
    if (!session.request_id) return;
    try {
      const res = await fetch(`/api/approvals/status/${session.request_id}`);
      if (res.ok) {
        const data = await res.json();
        setApprovalStatus(data);
      }
    } catch {
      // silent
    }
  }, [session.request_id]);

  useEffect(() => {
    if (!session.request_id) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchApprovalStatus();
    const interval = setInterval(fetchApprovalStatus, 5000);
    return () => clearInterval(interval);
  }, [session.request_id, fetchApprovalStatus]);

  // Determine active step based on approval status
  let activeStep = -1;
  if (isSubmitted) {
    activeStep = 0;
    if (approvalStatus) {
      const { summary } = approvalStatus;
      if (summary.approved > 0 && summary.pending > 0) activeStep = 1;
      if (summary.overall === 'fully_approved') activeStep = 3;
      else if (summary.pending === 0 && summary.total > 0) activeStep = 2;
      else if (summary.approved > 0) activeStep = 1;
      else activeStep = 1;
    }
  } else if (hasTemplate) {
    activeStep = 0;
  }

  return (
    <div className="flex flex-col w-full bg-white rounded-2xl overflow-hidden shadow-xl">
      <div className="flex-1 overflow-y-auto chat-scrollbar">
        {/* Identity Card */}
        {workday && (
          <div className="p-4 border-b border-gray-100">
            <div className="rounded-xl bg-gradient-to-br from-slate-800 to-slate-900 p-4 text-white">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center">
                  <User className="w-5 h-5 text-amber-400" />
                </div>
                <div>
                  <p className="font-semibold text-sm">{workday.name}</p>
                  <p className="text-[11px] text-white/60">{session.acf2_id}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div className="flex items-center gap-1.5 text-white/70">
                  <Building2 className="w-3 h-3 text-white/40" />
                  {workday.team}
                </div>
                <div className="flex items-center gap-1.5 text-white/70">
                  <Users className="w-3 h-3 text-white/40" />
                  {workday.manager}
                </div>
                <div className="flex items-center gap-1.5 text-white/70">
                  <Layers3 className="w-3 h-3 text-white/40" />
                  {workday.dept}
                </div>
                <div className="flex items-center gap-1.5 text-white/70">
                  <Clock className="w-3 h-3 text-white/40" />
                  {workday.employment_type}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Template section */}
        <div className="p-4 border-b border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900 text-sm">Access Template</h2>
            <span
              className={[
                'text-[10px] px-2 py-0.5 rounded-full font-medium',
                isSubmitted
                  ? 'text-blue-700 bg-blue-50'
                  : hasTemplate
                  ? 'text-green-700 bg-green-50'
                  : 'text-gray-400 bg-gray-100',
              ].join(' ')}
            >
              {isSubmitted ? 'Submitted' : hasTemplate ? 'Matched' : 'Waiting'}
            </span>
          </div>

          {template ? (
            <div className="space-y-4">
              {/* Template header */}
              <div className="rounded-xl border border-green-100 bg-green-50/50 p-3">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center flex-shrink-0">
                    <Layers3 className="w-4 h-4 text-green-700" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold text-gray-900 leading-snug">
                      {template.name}
                    </h3>
                    {resolvedRole && (
                      <p className="text-[11px] text-gray-500 mt-0.5 leading-snug">
                        {resolvedRole.team || 'Team pending'} -{' '}
                        {resolvedRole.employment_type || 'Type pending'}
                      </p>
                    )}
                    {template.confidence !== undefined && (
                      <div className="flex items-center gap-2 mt-2">
                        <div className="flex-1 h-1.5 bg-green-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-green-500 rounded-full"
                            style={{ width: `${Math.round(template.confidence * 100)}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-green-700 font-medium">
                          {Math.round(template.confidence * 100)}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Agent reasoning trace */}
              {agentTrace && !isSubmitted && (
                <AgentReasoningPanel trace={agentTrace} />
              )}

              {/* Consolidated summary */}
              <div className="rounded-lg bg-amber-50 border border-amber-100 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-amber-800">Bundle Summary</span>
                  <span className="text-[11px] font-bold text-amber-900">
                    {totalSelected} item{totalSelected !== 1 ? 's' : ''} selected
                  </span>
                </div>
                <div className="flex gap-3 mt-1 text-[10px] text-amber-700">
                  <span>{mandatoryCount} mandatory</span>
                  <span className="text-amber-300">|</span>
                  <span>{selectedOptionalCount} optional chosen</span>
                  <span className="text-amber-300">|</span>
                  <span>
                    {(template.optional_access.length - selectedOptionalCount)} optional skipped
                  </span>
                </div>
              </div>

              {/* Approval routing preview */}
              {workday && !isSubmitted && (
                <div className="rounded-lg border border-gray-100 px-3 py-2">
                  <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
                    Approval Routing
                  </p>
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-[11px] text-gray-700">
                      <div className="w-5 h-5 rounded-full bg-blue-50 flex items-center justify-center">
                        <Users className="w-3 h-3 text-blue-600" />
                      </div>
                      <span className="font-medium">{workday.manager}</span>
                      <span className="text-gray-400 ml-auto">Manager</span>
                    </div>
                    {template.mandatory_access.slice(0, 2).map((item) =>
                      item.owner_team ? (
                        <div key={item.id} className="flex items-center gap-2 text-[11px] text-gray-700">
                          <div className="w-5 h-5 rounded-full bg-purple-50 flex items-center justify-center">
                            <ShieldCheck className="w-3 h-3 text-purple-600" />
                          </div>
                          <span className="font-medium">{item.owner_team}</span>
                          <span className="text-gray-400 ml-auto">{item.system}</span>
                        </div>
                      ) : null
                    )}
                  </div>
                </div>
              )}

              {/* Access items grouped by system */}
              <AccessGroupBySystem
                title="Mandatory"
                items={template.mandatory_access}
                mandatory
                groupBySystem={groupBySystem}
              />
              <AccessGroupBySystem
                title="Optional"
                items={template.optional_access}
                mandatory={false}
                checkedIds={bundleIds}
                onToggle={isSubmitted ? undefined : toggleOptionalItem}
                groupBySystem={groupBySystem}
              />

              {/* Submit Button */}
              {hasTemplate && !isSubmitted && (
                <button
                  onClick={handleSubmit}
                  disabled={submitting || totalSelected === 0}
                  className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-gray-300 disabled:to-gray-400 text-white font-semibold py-3 px-4 rounded-xl transition-all shadow-lg shadow-blue-200 disabled:shadow-none text-sm"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      Submit Request ({totalSelected} items)
                    </>
                  )}
                </button>
              )}
            </div>
          ) : (
            <>
              <p className="text-[11px] text-gray-400 mb-3">
                {workday
                  ? 'Tell the assistant your role to see matching access templates.'
                  : 'Template matches will appear here after identity verification.'}
              </p>
              <div className="space-y-2.5">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="rounded-xl border border-gray-100 p-3 opacity-60 animate-pulse"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-gray-100 flex-shrink-0" />
                      <div className="flex-1 space-y-1.5">
                        <div className="h-2.5 bg-gray-100 rounded-full w-3/4" />
                        <div className="h-2 bg-gray-100 rounded-full w-1/2" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Legend */}
          {hasTemplate && !isSubmitted && (
            <div className="mt-4 flex items-center gap-3 text-[10px] text-gray-400">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded bg-green-200 inline-block" />
                Mandatory
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded border border-blue-300 inline-block" />
                Optional — click to toggle
              </span>
            </div>
          )}
        </div>

        {/* Approval Status (after submit) */}
        {isSubmitted && approvalStatus && (
          <div className="p-4 border-b border-gray-100">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-gray-900 text-sm">Approval Progress</h2>
              <span
                className={[
                  'text-[10px] px-2 py-0.5 rounded-full font-medium',
                  approvalStatus.summary.overall === 'fully_approved'
                    ? 'bg-green-50 text-green-700'
                    : approvalStatus.summary.overall === 'partially_rejected'
                    ? 'bg-red-50 text-red-700'
                    : 'bg-blue-50 text-blue-700',
                ].join(' ')}
              >
                {approvalStatus.summary.approved}/{approvalStatus.summary.total} approved
              </span>
            </div>

            {/* Progress bar */}
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden mb-3">
              <div
                className="h-full bg-gradient-to-r from-green-400 to-green-500 rounded-full transition-all duration-500"
                style={{
                  width: `${approvalStatus.summary.total > 0
                    ? (approvalStatus.summary.approved / approvalStatus.summary.total) * 100
                    : 0}%`,
                }}
              />
            </div>

            {teamsNotified && (
              <div className="rounded-lg bg-purple-50 border border-purple-100 px-3 py-2 mb-3 flex items-center gap-2">
                <Users className="w-3.5 h-3.5 text-purple-600" />
                <p className="text-[11px] text-purple-700 font-medium">
                  Manager notified via Microsoft Teams
                </p>
              </div>
            )}

            {/* Individual approval items */}
            <div className="space-y-2">
              {approvalStatus.events.map((event) => (
                <div
                  key={event.id}
                  className={[
                    'rounded-lg border px-3 py-2 flex items-center gap-2.5',
                    event.status === 'approved'
                      ? 'border-green-100 bg-green-50/50'
                      : event.status === 'rejected'
                      ? 'border-red-100 bg-red-50/50'
                      : 'border-gray-100',
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
                    <p className="text-[11px] font-medium text-gray-800 truncate">
                      {event.display_name}
                    </p>
                    <p className="text-[10px] text-gray-500">
                      {event.approver} · {event.status === 'pending' ? 'Awaiting' : event.status}
                    </p>
                  </div>
                  <span
                    className={[
                      'text-[9px] font-medium px-1.5 py-0.5 rounded-full',
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
              ))}
            </div>
          </div>
        )}

        {/* Status section */}
        <div className="p-4 flex-shrink-0">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900 text-sm">Request Status</h2>
            <span
              className={[
                'text-[10px] font-medium px-2 py-0.5 rounded-full',
                approvalStatus?.summary.overall === 'fully_approved'
                  ? 'bg-green-50 text-green-700'
                  : isSubmitted
                  ? 'bg-blue-50 text-blue-700'
                  : 'bg-gray-100 text-gray-400',
              ].join(' ')}
            >
              {approvalStatus?.summary.overall === 'fully_approved'
                ? 'Approved'
                : isSubmitted
                ? 'In Progress'
                : 'Not started'}
            </span>
          </div>

          {session.request_id && (
            <div className="rounded-lg bg-blue-50 border border-blue-100 px-3 py-2 mb-3 flex items-center gap-2">
              <Send className="w-3.5 h-3.5 text-blue-600" />
              <div>
                <p className="text-[11px] font-medium text-blue-800">Request Submitted</p>
                <p className="text-[10px] text-blue-600 font-mono">
                  {session.request_id.slice(0, 8)}...
                </p>
              </div>
            </div>
          )}

          <div className="relative">
            <div className="absolute left-[13px] top-5 bottom-5 w-px bg-gray-100" />

            {STEPS.map((step, i) => {
              const StepIcon = step.icon;
              const isActive = i <= activeStep;
              const isCurrent = i === activeStep;

              return (
                <div key={i} className="flex items-center gap-3 py-1.5 relative">
                  <div
                    className={[
                      'w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 z-10 transition-all',
                      isCurrent
                        ? 'bg-blue-500 shadow-md shadow-blue-200'
                        : isActive
                        ? 'bg-green-500'
                        : 'border-2 border-gray-200 bg-white',
                    ].join(' ')}
                  >
                    {isActive ? (
                      <StepIcon className="w-3.5 h-3.5 text-white" />
                    ) : (
                      <div className="w-2 h-2 rounded-full bg-gray-200" />
                    )}
                  </div>
                  <span
                    className={[
                      'text-xs',
                      isCurrent
                        ? 'text-blue-700 font-semibold'
                        : isActive
                        ? 'text-green-700 font-medium'
                        : 'text-gray-400',
                    ].join(' ')}
                  >
                    {step.label}
                  </span>
                  {isCurrent && (
                    <span className="ml-auto text-[9px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded-full font-medium">
                      Current
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Access Items Grouped by System ──────────────────────────────────────────

function AccessGroupBySystem({
  title,
  items,
  mandatory,
  checkedIds,
  onToggle,
  groupBySystem,
}: {
  title: string;
  items: AccessItem[];
  mandatory: boolean;
  checkedIds?: string[];
  onToggle?: (item: AccessItem) => void;
  groupBySystem: (items: AccessItem[]) => Record<string, AccessItem[]>;
}) {
  if (!items.length) return null;

  const groups = groupBySystem(items);
  const systemNames = Object.keys(groups).sort();

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">
          {title}
        </h3>
        <span className="text-[10px] text-gray-400">{items.length}</span>
      </div>
      <div className="space-y-3">
        {systemNames.map((system) => (
          <div key={system}>
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-gray-300 inline-block" />
              {system}
            </p>
            <div className="space-y-1.5 pl-3">
              {groups[system].map((item) => {
                const isChecked = mandatory || (checkedIds?.includes(item.id) ?? false);
                const isToggleable = !mandatory && Boolean(onToggle);

                return (
                  <div
                    key={item.id}
                    className={[
                      'rounded-lg border px-3 py-2 transition-colors',
                      isToggleable ? 'cursor-pointer select-none' : '',
                      isToggleable && isChecked
                        ? 'border-blue-200 bg-blue-50/40 hover:bg-blue-50/60'
                        : isToggleable
                        ? 'border-gray-100 hover:border-blue-100 hover:bg-blue-50/20'
                        : 'border-gray-100',
                    ].join(' ')}
                    onClick={isToggleable ? () => onToggle!(item) : undefined}
                  >
                    <div className="flex items-center gap-2">
                      {isChecked ? (
                        <CheckCircle2
                          className={[
                            'w-3.5 h-3.5 flex-shrink-0',
                            mandatory ? 'text-green-600' : 'text-blue-500',
                          ].join(' ')}
                        />
                      ) : (
                        <Circle className="w-3.5 h-3.5 text-gray-300 flex-shrink-0" />
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="text-[11px] font-medium text-gray-800 leading-snug">
                          {item.name}
                        </p>
                        {item.reason && (
                          <p className="text-[10px] text-gray-400 leading-snug mt-0.5">
                            {item.reason}
                          </p>
                        )}
                      </div>
                      {item.owner_team && (
                        <span className="text-[9px] text-gray-400 flex-shrink-0">
                          {item.owner_team}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
