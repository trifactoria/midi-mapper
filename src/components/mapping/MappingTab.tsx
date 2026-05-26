import { useMemo, useState } from "react";
import { ActiveBindingsList } from "../bindings/ActiveBindingsList";
import { RunHistoryPreview } from "../history/RunHistoryPreview";
import type { BackendActionRunResult, BackendBindingCreatePayload } from "../v2/api";
import type {
  AutomationState,
  CcBar,
  KeyboardNote,
  MidiMonitorEvent,
  V2BindingSummary,
  V2RunSummary,
} from "../v2/types";
import { CcFaderPanel } from "./CcFaderPanel";
import { KeyboardGrid } from "./KeyboardGrid";
import { MidiInputMonitor } from "./MidiInputMonitor";
import { QuickBindPanel } from "./QuickBindPanel";

type Props = {
  events: MidiMonitorEvent[];
  notes: KeyboardNote[];
  bars: CcBar[];
  bindings: V2BindingSummary[];
  runs: V2RunSummary[];
  automation: AutomationState;
  canMutateBindings: boolean;
  onCreateBinding: (payload: BackendBindingCreatePayload) => Promise<V2BindingSummary>;
  onDryRunAction: (actionId: string) => Promise<BackendActionRunResult>;
  onTestAction: (actionId: string) => Promise<BackendActionRunResult>;
  onDeleteBinding: (bindingId: string) => Promise<void>;
  liveMatchedBindingId?: string | null;
};

function SectionHeader({
  title,
  count,
  trailing,
}: {
  title: string;
  count?: number;
  trailing?: React.ReactNode;
}) {
  return (
    <div className="mb-1.5 flex items-center justify-between gap-2">
      <h3 className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/65">
        {title}
        {typeof count === "number" && (
          <span className="rounded bg-white/[0.06] !px-1 !py-px font-mono text-[10px] text-white/60">
            {count}
          </span>
        )}
      </h3>
      {trailing}
    </div>
  );
}

export function MappingTab({
  events,
  notes,
  bars,
  bindings,
  runs,
  automation,
  canMutateBindings,
  onCreateBinding,
  onDryRunAction,
  onTestAction,
  onDeleteBinding,
  liveMatchedBindingId,
}: Props) {
  const [selectedBindingId, setSelectedBindingId] = useState<string | null>(null);
  const highlightedBindingId = selectedBindingId ?? liveMatchedBindingId ?? null;
  const selectedBinding = useMemo(
    () => bindings.find((binding) => binding.id === selectedBindingId) ?? null,
    [bindings, selectedBindingId],
  );

  return (
    <div className="space-y-2">
      <MidiInputMonitor events={events} automation={automation} />

      <div className="grid gap-2.5 xl:grid-cols-[284px_minmax(0,1fr)] 2xl:grid-cols-[300px_minmax(0,1fr)_336px]">
        {/* Column 1 — Binding editor */}
        <div className="order-2 min-w-0 space-y-2 xl:order-1">
          <QuickBindPanel
            selectedBinding={selectedBinding}
            canMutateBindings={canMutateBindings}
            onCreateBinding={onCreateBinding}
            onDryRunAction={onDryRunAction}
            onTestAction={onTestAction}
            onBindingCreated={(binding) => setSelectedBindingId(binding.id)}
          />
        </div>

        {/* Column 2 — Note map + control map */}
        <div className="order-1 min-w-0 space-y-2 xl:order-2">
          <KeyboardGrid notes={notes} />
          <CcFaderPanel bars={bars} />
        </div>

        {/* Column 3 — Active bindings + run history (stacks under center on xl, side at 2xl) */}
        <div className="order-3 grid min-w-0 gap-2 xl:grid-cols-2 2xl:grid-cols-1">
          <section className="rounded-md border border-white/8 bg-white/[0.014] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.018),inset_0_0_24px_rgba(0,0,0,0.18)]">
            <SectionHeader
              title="Active Bindings"
              count={bindings.length}
              trailing={
                <select
                  aria-label="Filter bindings"
                  className="!h-6 rounded !border-white/10 !bg-white/[0.03] !px-1.5 !py-0 !text-[10.5px] text-white/70"
                  defaultValue="all"
                >
                  <option value="all">All Types</option>
                  <option value="note">Note</option>
                  <option value="cc">CC</option>
                </select>
              }
            />
            <input
              type="search"
              placeholder="Search bindings..."
              className="mb-2 block w-full !text-[11.5px]"
              aria-label="Search bindings"
            />
            <ActiveBindingsList
              bindings={bindings}
              selectedBindingId={highlightedBindingId}
              onSelectBinding={(binding) => setSelectedBindingId(binding.id)}
              onDeleteBinding={(binding) => {
                void onDeleteBinding(binding.id).then(() => {
                  setSelectedBindingId((current) => (current === binding.id ? null : current));
                });
              }}
            />
          </section>

          <section className="rounded-md border border-white/8 bg-white/[0.014] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.018),inset_0_0_24px_rgba(0,0,0,0.18)]">
            <SectionHeader
              title="Run History"
              trailing={
                <button
                  type="button"
                  className="!h-6 rounded-md border border-white/10 bg-white/[0.03] !px-2 !text-[10.5px] text-white/75 hover:bg-white/[0.06]"
                >
                  View All
                </button>
              }
            />
            <RunHistoryPreview runs={runs} />
          </section>
        </div>
      </div>
    </div>
  );
}
