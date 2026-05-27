import { useMemo, useRef, useState } from "react";
import { ActiveBindingsList } from "../bindings/ActiveBindingsList";
import { EditBindingModal } from "../bindings/EditBindingModal";
import { ConfirmDialog } from "../ConfirmDialog";
import { RunHistoryPreview } from "../history/RunHistoryPreview";
import type { BackendActionRunResult, BackendBindingCreatePayload, BackendBindingPatch } from "../v2/api";
import type {
  AutomationState,
  CcBar,
  KeyboardNote,
  MidiMonitorEvent,
  V2BindingSummary,
  V2MidiEventPayload,
  V2RunSummary,
} from "../v2/types";
import { CcFaderPanel } from "./CcFaderPanel";
import { KeyboardGrid } from "./KeyboardGrid";
import { MidiInputMonitor } from "./MidiInputMonitor";
import { QuickBindPanel, type TileCapture } from "./QuickBindPanel";

type Props = {
  events: MidiMonitorEvent[];
  notes: KeyboardNote[];
  bars: CcBar[];
  bindings: V2BindingSummary[];
  runs: V2RunSummary[];
  automation: AutomationState;
  canMutateBindings: boolean;
  onCreateBinding: (payload: BackendBindingCreatePayload) => Promise<V2BindingSummary>;
  onEditBinding?: (bindingId: string, patch: BackendBindingPatch) => Promise<void>;
  onToggleBindingEnabled?: (bindingId: string) => void;
  onDuplicateBinding?: (bindingId: string) => Promise<V2BindingSummary | null>;
  onDryRunAction: (actionId: string) => Promise<BackendActionRunResult>;
  onTestAction: (actionId: string) => Promise<BackendActionRunResult>;
  onDeleteBinding: (bindingId: string) => Promise<void>;
  onClearRuns?: () => Promise<void>;
  onKeygrabChange?: (enabled: boolean) => void;
  onMouseModeChange?: (mouseMode: boolean) => void;
  onClearEvents?: () => void;
  onSimulateNote?: (note: number) => void;
  selectedInputPort?: string | null;
  liveMatchedBindingId?: string | null;
  lastMidiEvent?: V2MidiEventPayload | null;
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
  onEditBinding,
  onToggleBindingEnabled,
  onDuplicateBinding,
  onDryRunAction,
  onTestAction,
  onDeleteBinding,
  onClearRuns,
  onKeygrabChange,
  onMouseModeChange,
  onClearEvents,
  onSimulateNote,
  selectedInputPort,
  liveMatchedBindingId,
  lastMidiEvent,
}: Props) {
  const [selectedBindingId, setSelectedBindingId] = useState<string | null>(null);
  const [editingBinding, setEditingBinding] = useState<V2BindingSummary | null>(null);
  const [clearRunsOpen, setClearRunsOpen] = useState(false);
  const tileCaptureKeyRef = useRef(0);
  const [tileCapture, setTileCapture] = useState<TileCapture | null>(null);

  function handleNoteClick(note: number) {
    if (!automation.mouseMode) return;
    onSimulateNote?.(note);
    const matching = bindings.filter(
      (b) => b.kind === "note" && b.note === note && b.enabled && b.actionId,
    );
    for (const b of matching) {
      void onTestAction(b.actionId!).catch(() => {});
    }
    setTileCapture({ type: "note", value: note, key: ++tileCaptureKeyRef.current });
  }
  function handleCcClick(controller: number) {
    if (!automation.mouseMode) return;
    setTileCapture({ type: "cc", value: controller, key: ++tileCaptureKeyRef.current });
  }
  const highlightedBindingId = selectedBindingId ?? liveMatchedBindingId ?? null;
  const selectedBinding = useMemo(
    () => bindings.find((binding) => binding.id === selectedBindingId) ?? null,
    [bindings, selectedBindingId],
  );

  return (
    <div className="space-y-2">
      <MidiInputMonitor
        events={events}
        automation={automation}
        selectedInputPort={selectedInputPort}
        onKeygrabChange={onKeygrabChange}
        onMouseModeChange={onMouseModeChange}
        onClearEvents={onClearEvents}
      />

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
            lastMidiEvent={lastMidiEvent}
            tileCapture={tileCapture}
          />
        </div>

        {/* Column 2 — Note map + control map */}
        <div className="order-1 min-w-0 space-y-2 xl:order-2">
          <KeyboardGrid notes={notes} onNoteClick={automation.mouseMode ? handleNoteClick : undefined} />
          <CcFaderPanel bars={bars} onCcClick={automation.mouseMode ? handleCcClick : undefined} />
        </div>

        {/* Column 3 — Active bindings + run history (stacks under center on xl, side at 2xl) */}
        <div className="order-3 grid min-w-0 gap-2 xl:grid-cols-2 xl:items-start 2xl:grid-cols-1">
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
            <div className="max-h-96 overflow-y-auto">
              <ActiveBindingsList
                bindings={bindings}
                selectedBindingId={highlightedBindingId}
                onSelectBinding={(binding) => setSelectedBindingId(binding.id)}
                onEditBinding={(binding) => setEditingBinding(binding)}
                onToggleEnabled={onToggleBindingEnabled ? (binding) => onToggleBindingEnabled(binding.id) : undefined}
                onDuplicateBinding={onDuplicateBinding ? (binding) => {
                  void onDuplicateBinding(binding.id).then((dup) => {
                    if (dup) setEditingBinding(dup);
                  });
                } : undefined}
                onDeleteBinding={(binding) => {
                  void onDeleteBinding(binding.id).then(() => {
                    setSelectedBindingId((current) => (current === binding.id ? null : current));
                  });
                }}
              />
            </div>
          </section>

          <section className="rounded-md border border-white/8 bg-white/[0.014] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.018),inset_0_0_24px_rgba(0,0,0,0.18)]">
            <SectionHeader
              title="Run History"
              count={runs.length}
              trailing={
                <div className="flex items-center gap-1">
                  {runs.length > 0 && onClearRuns && (
                    <button
                      type="button"
                      onClick={() => setClearRunsOpen(true)}
                      className="!h-6 rounded-md border border-white/10 !px-2 !text-[10.5px] text-white/55 hover:text-white/80"
                      style={{ background: "rgba(255,255,255,0.03)" }}
                    >
                      Clear
                    </button>
                  )}
                </div>
              }
            />
            <div className="max-h-64 overflow-y-auto">
              <RunHistoryPreview runs={runs} />
            </div>
          </section>
        </div>
      </div>
      <ConfirmDialog
        open={clearRunsOpen}
        message="Clear all run history?"
        confirmLabel="Clear"
        onConfirm={() => { setClearRunsOpen(false); void onClearRuns?.(); }}
        onCancel={() => setClearRunsOpen(false)}
      />
      {editingBinding && onEditBinding && (
        <EditBindingModal
          key={editingBinding.id}
          binding={editingBinding}
          onSave={onEditBinding}
          onCancel={() => setEditingBinding(null)}
        />
      )}
    </div>
  );
}
