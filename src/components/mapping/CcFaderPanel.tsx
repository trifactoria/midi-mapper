import type { PointerEvent, WheelEvent } from "react";
import type { CcBar } from "../v2/types";

type Props = {
  bars: CcBar[];
  onCcChange?: (controller: number, value: number) => void;
};

const BAR_COLOR = {
  cyan: "bg-cyan-300 shadow-[0_0_8px_rgba(0,212,255,0.55)]",
  emerald: "bg-emerald-300 shadow-[0_0_8px_rgba(52,211,153,0.55)]",
  amber: "bg-amber-300 shadow-[0_0_8px_rgba(252,211,77,0.55)]",
  orange: "bg-orange-400 shadow-[0_0_8px_rgba(251,146,60,0.55)]",
  purple: "bg-purple-300 shadow-[0_0_8px_rgba(192,132,252,0.55)]",
  red: "bg-rose-400 shadow-[0_0_8px_rgba(244,114,128,0.55)]",
} as const;

function valueFromPointer(event: PointerEvent<HTMLDivElement>): number {
  const rect = event.currentTarget.getBoundingClientRect();
  const pct = 1 - (event.clientY - rect.top) / rect.height;
  return Math.max(0, Math.min(127, Math.round(pct * 127)));
}

export function CcFaderPanel({ bars, onCcChange }: Props) {
  return (
    <section className="rounded-md border border-white/12 bg-white/[0.038] px-3 pb-2 pt-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.055),0_6px_22px_-8px_rgba(0,0,0,0.6)]">
      <div className="mb-1.5 flex items-center justify-between">
        <h3 className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/65">
          Control Map (CC)
        </h3>
        <span className="text-[10px] uppercase tracking-[0.12em] text-white/40">{bars.length} CC controls</span>
      </div>

      <div className="rounded-md border border-white/8 bg-black/35 p-2.5">
        <div className="mb-1 grid grid-cols-[repeat(16,minmax(0,1fr))] gap-1 font-mono text-[9.5px] text-white/40">
          {bars.map((bar) => (
            <div key={bar.index} className="text-center">
              {bar.index}
            </div>
          ))}
        </div>

        <div className="grid h-28 grid-cols-[repeat(16,minmax(0,1fr))] items-end gap-1">
          {bars.map((bar) => {
            const hasData = Boolean(bar.color);
            const visualValue = hasData ? bar.value : 64;
            const pct = Math.round((visualValue / 127) * 100);
            const color = hasData ? BAR_COLOR[bar.color ?? "cyan"] : "bg-white/20";
            return (
              <div
                key={bar.index}
                className={["relative flex h-full touch-none flex-col justify-end overflow-hidden rounded-sm bg-white/[0.025]", onCcChange ? "cursor-ns-resize hover:ring-1 hover:ring-white/20" : ""].join(" ").trim()}
                title={hasData ? `CC ${bar.index} · value ${bar.value}` : `CC ${bar.index} · waiting for data`}
                onPointerDown={(event) => {
                  if (!onCcChange) return;
                  event.currentTarget.setPointerCapture(event.pointerId);
                  onCcChange(bar.index, valueFromPointer(event));
                }}
                onPointerMove={(event) => {
                  if (!onCcChange || !event.currentTarget.hasPointerCapture(event.pointerId)) return;
                  onCcChange(bar.index, valueFromPointer(event));
                }}
                onWheel={(event: WheelEvent<HTMLDivElement>) => {
                  if (!onCcChange) return;
                  event.preventDefault();
                  const direction = event.deltaY > 0 ? -1 : 1;
                  onCcChange(bar.index, Math.max(0, Math.min(127, bar.value + direction * 4)));
                }}
                role={onCcChange ? "slider" : undefined}
                aria-valuemin={onCcChange ? 0 : undefined}
                aria-valuemax={onCcChange ? 127 : undefined}
                aria-valuenow={onCcChange ? bar.value : undefined}
                tabIndex={onCcChange ? 0 : undefined}
              >
                <div
                  className={["w-full rounded-sm transition-all", color].join(" ")}
                  style={{ height: `${Math.max(pct, hasData ? 4 : 0)}%` }}
                />
              </div>
            );
          })}
        </div>

        <div className="mt-1 grid grid-cols-[repeat(16,minmax(0,1fr))] gap-1 font-mono text-[9.5px] text-white/75 tabular-nums">
          {bars.map((bar) => (
            <div key={bar.index} className="text-center">
              {bar.color ? bar.value : "—"}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
