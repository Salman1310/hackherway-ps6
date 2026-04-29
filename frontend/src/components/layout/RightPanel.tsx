const steps = [
  { label: 'Request Created' },
  { label: 'Manager Approval' },
  { label: 'Team Approval' },
  { label: 'Provisioned' },
];

export default function RightPanel() {
  return (
    <div className="flex flex-col w-full bg-white rounded-2xl overflow-hidden shadow-xl">
      {/* Template section */}
      <div className="flex-1 p-4 border-b border-gray-100 overflow-y-auto chat-scrollbar">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-900 text-sm">Access Template</h2>
          <span className="text-[10px] text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
            Waiting
          </span>
        </div>

        <p className="text-[11px] text-gray-400 mb-3">
          Template matches will appear here after role confirmation.
        </p>

        {/* Skeleton cards */}
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

        {/* Legend */}
        <div className="mt-4 flex items-center gap-3 text-[10px] text-gray-400">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded bg-gray-200 inline-block" />
            Mandatory
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded border border-gray-300 inline-block" />
            Optional
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
