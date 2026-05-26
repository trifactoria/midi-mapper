import type { V2BindingSummary } from "../v2/types";

type Props = {
  bindings: V2BindingSummary[];
  compact?: boolean;
  selectedBindingId?: string | null;
  onSelectBinding?: (binding: V2BindingSummary) => void;
  onDeleteBinding?: (binding: V2BindingSummary) => void;
};

function KindBadge({ kind }: { kind: V2BindingSummary["kind"] }) {
  if (kind === "cc") {
    return (
      <span className="inline-flex !h-4 items-center rounded border border-amber-300/25 bg-amber-300/[0.08] !px-1 font-mono text-[9.5px] uppercase tracking-[0.12em] text-amber-200">
        CC
      </span>
    );
  }
  return (
    <span className="inline-flex !h-4 items-center rounded border border-cyan-300/25 bg-cyan-300/[0.08] !px-1 font-mono text-[9.5px] uppercase tracking-[0.12em] text-cyan-200">
      Note
    </span>
  );
}

function KindGlyph({ kind }: { kind: V2BindingSummary["kind"] }) {
  if (kind === "cc") {
    return (
      <span className="grid h-6 w-6 shrink-0 place-items-center rounded border border-amber-300/20 bg-amber-300/[0.06] text-amber-200">
        <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.6">
          <circle cx="8" cy="8" r="4.5" />
          <path d="M8 3.5v2M8 10.5v2M3.5 8h2M10.5 8h2" />
        </svg>
      </span>
    );
  }
  return (
    <span className="grid h-6 w-6 shrink-0 place-items-center rounded border border-cyan-300/20 bg-cyan-300/[0.06] text-cyan-200">
      <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.6">
        <path d="M5 3v8.5a2 2 0 1 1-2-2H5V3l8-1v8.5a2 2 0 1 1-2-2H13" />
      </svg>
    </span>
  );
}

export function ActiveBindingsList({
  bindings,
  compact = false,
  selectedBindingId,
  onSelectBinding,
  onDeleteBinding,
}: Props) {
  return (
    <div className="space-y-1">
      {bindings.map((binding) => (
        <article
          key={binding.id}
          onClick={() => onSelectBinding?.(binding)}
          className={[
            "rounded-md border bg-zinc-900/65 px-2 py-1.5 transition",
            selectedBindingId === binding.id
              ? "border-cyan-300/25 shadow-[inset_0_0_0_1px_rgba(0,180,210,0.12)]"
              : binding.enabled
              ? "border-white/10 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.02)]"
              : "border-white/6 opacity-70",
          ].join(" ")}
        >
          <div className="flex items-center gap-2">
            <KindGlyph kind={binding.kind} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5 leading-none">
                <span className="truncate font-mono text-[11.5px] font-semibold tracking-tight text-white">
                  {binding.triggerLabel}
                </span>
                {binding.triggerCondition && (
                  <span className="font-mono text-[10px] text-white/40">{binding.triggerCondition}</span>
                )}
              </div>
              <div className="mt-[3px] flex items-center gap-1 leading-none">
                <span className="text-cyan-300/55" aria-hidden>→</span>
                <span className="truncate font-mono text-[10.5px] text-white/55">
                  {binding.actionLabel}
                </span>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              <KindBadge kind={binding.kind} />
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onDeleteBinding?.(binding);
                }}
                className="grid !h-5 !w-5 place-items-center rounded border border-white/8 bg-white/[0.03] !p-0 text-white/45 hover:bg-white/[0.06]"
                aria-label="Delete binding"
              >
                <svg viewBox="0 0 16 16" className="h-3 w-3" fill="currentColor">
                  <circle cx="8" cy="3.5" r="1" />
                  <circle cx="8" cy="8" r="1" />
                  <circle cx="8" cy="12.5" r="1" />
                </svg>
              </button>
            </div>
          </div>

          {!compact && (
            <div className="mt-1.5 flex items-center justify-between gap-2 border-t border-white/[0.04] pt-1 text-[10px] leading-none">
              <span className="truncate">
                <span className="uppercase tracking-[0.14em] text-white/25">Layer </span>
                <span className="text-white/65">{binding.layer}</span>
              </span>
              <div className="flex shrink-0 items-center gap-1">
                <span
                  className={[
                    "inline-flex items-center gap-1 rounded border !px-1.5 !py-[3px] text-[9.5px] uppercase tracking-[0.12em]",
                    binding.enabled
                      ? "border-emerald-300/25 bg-emerald-400/[0.05] text-emerald-100/90"
                      : "border-white/10 bg-white/[0.03] text-white/40",
                  ].join(" ")}
                >
                  <span
                    className={[
                      "h-1 w-1 rounded-full",
                      binding.enabled ? "bg-emerald-300 shadow-[0_0_5px_rgba(52,200,150,0.6)]" : "bg-white/30",
                    ].join(" ")}
                  />
                  {binding.enabled ? "Active" : "Off"}
                </span>
                <span
                  className={[
                    "rounded border !px-1.5 !py-[3px] text-[9.5px] uppercase tracking-[0.12em]",
                    binding.requireArmed
                      ? "border-white/12 bg-white/[0.05] text-white/70"
                      : "border-white/10 bg-white/[0.03] text-white/40",
                  ].join(" ")}
                >
                  {binding.requireArmed ? "Armed" : "Always"}
                </span>
              </div>
            </div>
          )}
        </article>
      ))}
    </div>
  );
}
