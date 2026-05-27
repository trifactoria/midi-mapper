import type { AutomationState, MidiMonitorEvent } from "../v2/types";

type Props = {
  events: MidiMonitorEvent[];
  automation: AutomationState;
  selectedInputPort?: string | null;
  onKeygrabChange?: (enabled: boolean) => void;
  onMouseModeChange?: (mouseMode: boolean) => void;
  onClearEvents?: () => void;
};

function Pill({ label, on, onClick }: { label: string; on: boolean; onClick?: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "flex !h-7 items-center gap-1.5 rounded-md border !px-2 !text-[10px] uppercase tracking-[0.12em]",
        on
          ? "border-emerald-300/30 bg-emerald-400/[0.08] text-emerald-100"
          : "border-white/10 bg-white/[0.03] text-white/55",
        onClick ? "cursor-pointer hover:opacity-80" : "cursor-default",
      ].join(" ")}
      aria-pressed={on}
    >
      <span>{label}</span>
      <span
        className={[
          "relative inline-flex h-3.5 w-6 shrink-0 rounded-full transition",
          on ? "bg-emerald-400/80 shadow-[0_0_10px_rgba(52,211,153,0.45)]" : "bg-white/15",
        ].join(" ")}
        aria-hidden
      >
        <span
          className={[
            "absolute top-0.5 h-2.5 w-2.5 rounded-full bg-white transition",
            on ? "left-[12px]" : "left-0.5",
          ].join(" ")}
        />
      </span>
    </button>
  );
}

export function MidiInputMonitor({
  events,
  automation,
  selectedInputPort,
  onKeygrabChange,
  onMouseModeChange,
  onClearEvents,
}: Props) {
  const last = events[0];

  const badgeLabel = !last ? "Listening" : last.matched ? "Matched" : "Live";
  const badgeClass = !last
    ? "border-white/15 bg-white/[0.05] text-white/50"
    : last.matched
    ? "border-emerald-300/30 bg-emerald-400/[0.08] text-emerald-100"
    : "border-cyan-300/25 bg-cyan-300/[0.07] text-cyan-200";
  const dotClass = !last
    ? "bg-white/30"
    : last.matched
    ? "bg-emerald-300 shadow-[0_0_8px_rgba(52,211,153,0.65)]"
    : "bg-cyan-300 shadow-[0_0_8px_rgba(0,200,255,0.55)]";

  const portLabel = selectedInputPort ?? last?.port ?? "";

  return (
    <section className="rounded-md border border-white/10 bg-white/[0.025] p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.04),0_2px_10px_-6px_rgba(0,0,0,0.45)]">
      <div className="mb-1.5 flex items-center justify-between">
        <h3 className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/55">
          Input Monitor
        </h3>
        {!last && (
          <span className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.12em] text-white/35">
            <span className="h-1.5 w-1.5 rounded-full bg-white/25" />
            Waiting for MIDI data...
          </span>
        )}
        {last && (
          <span className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.12em] text-emerald-100/70">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_8px_rgba(52,211,153,0.65)]" />
            Listening
          </span>
        )}
      </div>

      <div className="grid items-center gap-2.5 lg:grid-cols-[minmax(0,1fr)_auto]">
        <div className="flex min-w-0 items-center gap-2.5 rounded-md border border-white/10 bg-black/35 px-2.5 py-1.5">
          <span
            className={[
              "inline-flex shrink-0 items-center gap-1 rounded border !px-1.5 !py-px text-[9.5px] uppercase tracking-[0.12em]",
              badgeClass,
            ].join(" ")}
          >
            <span className={["h-1 w-1 rounded-full", dotClass].join(" ")} />
            {badgeLabel}
          </span>
          <span className="truncate font-mono text-[12.5px] text-white/90">
            {last
              ? `${last.type} · Ch ${last.channel} · ${last.value}`
              : "Waiting for MIDI data..."}
          </span>
          {portLabel && (
            <span className="ml-auto hidden shrink-0 truncate font-mono text-[10.5px] text-white/40 md:inline">
              {portLabel}
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-end gap-1.5">
          <Pill
            label="Keygrab"
            on={automation.keygrab}
            onClick={onKeygrabChange ? () => onKeygrabChange(!automation.keygrab) : undefined}
          />
          <Pill
            label="Mouse Mode"
            on={automation.mouseMode}
            onClick={onMouseModeChange ? () => onMouseModeChange(!automation.mouseMode) : undefined}
          />
          <button
            type="button"
            onClick={onClearEvents}
            className="!h-7 rounded-md border border-white/10 bg-white/[0.03] !px-2.5 !text-[10px] uppercase tracking-[0.12em] text-white/70 hover:bg-white/[0.06]"
          >
            Clear
          </button>
        </div>
      </div>
    </section>
  );
}
