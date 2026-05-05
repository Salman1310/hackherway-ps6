'use client';

import { CheckCircle2, Circle, Layers3 } from 'lucide-react';
import { useSession } from '@/contexts/SessionContext';
import type { AccessItem } from '@/lib/types';

const steps = [
  { label: 'Request Created' },
  { label: 'Manager Approval' },
  { label: 'Team Approval' },
  { label: 'Provisioned' },
];

export default function RightPanel() {
  const { session, setSession } = useSession();
  const template = session.selected_template;
  const resolvedRole = session.resolved_role;
  const hasTemplate = Boolean(template);

  // IDs of items currently in the final bundle
  const bundleIds = session.final_bundle
    .filter((i) => i && i.id)
    .map((i) => i.id);

  const toggleOptionalItem = (item: AccessItem) => {
    setSession((prev) => {
      const isChecked = prev.final_bundle.some((i) => i.id === item.id);
      const newBundle = isChecked
        ? prev.final_bundle.filter((i) => i.id !== item.id)
        : [...prev.final_bundle, item];
      return { ...prev, final_bundle: newBundle };
    });
  };

  return (
    <div className="flex flex-col w-full bg-white rounded-2xl overflow-hidden shadow-xl">
      {/* Template section */}
      <div className="flex-1 p-4 border-b border-gray-100 overflow-y-auto chat-scrollbar">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-900 text-sm">Access Template</h2>
          <span
            className={[
              'text-[10px] px-2 py-0.5 rounded-full',
              hasTemplate ? 'text-green-700 bg-green-50' : 'text-gray-400 bg-gray-100',
            ].join(' ')}
          >
            {hasTemplate ? 'Matched' : 'Waiting'}
          </span>
        </div>

        {template ? (
          <div className="space-y-4">
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
                      {resolvedRole.employment_type || 'Employment type pending'}
                    </p>
                  )}
                  {template.confidence !== undefined && (
                    <p className="text-[10px] text-green-700 mt-2">
                      Confidence {Math.round(template.confidence * 100)}%
                    </p>
                  )}
                </div>
              </div>
            </div>

            <AccessGroup
              title="Mandatory"
              items={template.mandatory_access}
              mandatory
            />
            <AccessGroup
              title="Optional"
              items={template.optional_access}
              mandatory={false}
              checkedIds={bundleIds}
              onToggle={toggleOptionalItem}
            />
          </div>
        ) : (
          <>
            <p className="text-[11px] text-gray-400 mb-3">
              Template matches will appear here after role confirmation.
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
                    <div className="w-4 h-4 rounded bg-gray-100 flex-shrink-0" />
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Legend */}
        <div className="mt-4 flex items-center gap-3 text-[10px] text-gray-400">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded bg-gray-200 inline-block" />
            Mandatory
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded border border-gray-300 inline-block" />
            Optional — click to toggle
          </span>
        </div>
      </div>

      {/* Status section */}
      <div className="p-4 flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-900 text-sm">Request Status</h2>
          <span className="text-[10px] text-gray-400">Not started</span>
        </div>

        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[13px] top-5 bottom-5 w-px bg-gray-100" />

          {steps.map((step, i) => (
            <div key={i} className="flex items-center gap-3 py-1.5 relative">
              <div className="w-7 h-7 rounded-full border-2 border-gray-200 bg-white flex items-center justify-center flex-shrink-0 z-10">
                <div className="w-2 h-2 rounded-full bg-gray-200" />
              </div>
              <span className="text-xs text-gray-400">{step.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function AccessGroup({
  title,
  items,
  mandatory,
  checkedIds,
  onToggle,
}: {
  title: string;
  items: AccessItem[];
  mandatory: boolean;
  checkedIds?: string[];
  onToggle?: (item: AccessItem) => void;
}) {
  if (!items.length) {
    return null;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">
          {title}
        </h3>
        <span className="text-[10px] text-gray-400">{items.length}</span>
      </div>
      <div className="space-y-2">
        {items.map((item) => {
          const isChecked = mandatory || (checkedIds?.includes(item.id) ?? false);
          const isToggleable = !mandatory && Boolean(onToggle);

          return (
            <div
              key={item.id}
              className={[
                'rounded-xl border p-3 transition-colors',
                isToggleable
                  ? 'cursor-pointer select-none'
                  : '',
                isToggleable && isChecked
                  ? 'border-blue-200 bg-blue-50/40 hover:bg-blue-50/60'
                  : isToggleable
                  ? 'border-gray-100 hover:border-blue-100 hover:bg-blue-50/20'
                  : 'border-gray-100',
              ].join(' ')}
              onClick={isToggleable ? () => onToggle!(item) : undefined}
            >
              <div className="flex items-start gap-2.5">
                {isChecked ? (
                  <CheckCircle2
                    className={[
                      'w-4 h-4 mt-0.5 flex-shrink-0',
                      mandatory ? 'text-green-600' : 'text-blue-500',
                    ].join(' ')}
                  />
                ) : (
                  <Circle className="w-4 h-4 text-gray-300 mt-0.5 flex-shrink-0" />
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-gray-800 leading-snug">
                    {item.name}
                  </p>
                  <p className="text-[10px] text-gray-400 mt-0.5 leading-snug">
                    {item.system}
                    {item.owner_team ? ` - ${item.owner_team}` : ''}
                  </p>
                  {item.reason && (
                    <p className="text-[10px] text-gray-500 mt-1.5 leading-snug">
                      {item.reason}
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
