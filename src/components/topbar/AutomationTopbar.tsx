"use client";

import type { AutomationState } from "../v2/types";

type Props = {
  state: AutomationState;
};

function Switch({ on, size = "md" }: { on: boolean; size?: "sm" | "md" }) {
  const wrap = size === "sm" ? "h-4 w-7" : "h-[18px] w-8";
  const knob = size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5";
  const knobLeft = size === "sm" ? (on ? "left-[14px]" : "left-0.5") : on ? "left-[16px]" : "left-0.5";
  return (
    <span
      className={[
        "relative inline-flex shrink-0 rounded-full border transition",
        wrap,
        on
          ? "border-emerald-300/40 bg-emerald-400/80 shadow-[0_0_12px_rgba(52,211,153,0.45)]"
          : "border-white/10 bg-white/[0.08]",
      ].join(" ")}
      aria-hidden
    >
      <span
        className={[
          "absolute top-0.5 rounded-full bg-white transition",
          knob,
          knobLeft,
        ].join(" ")}
      />
    </span>
  );
}

function ToggleLine({ label, on }: { label: string; on: boolean }) {
  return (
    <button
      type="button"
      className={[
        "flex !h-8 items-center gap-2 rounded-md border !px-2.5 !text-[10.5px] uppercase tracking-[0.10em]",
        on
          ? "border-white/12 bg-white/[0.04] text-white/85"
          : "border-white/10 bg-white/[0.02] text-white/55",
      ].join(" ")}
      aria-pressed={on}
    >
      <span
        className={[
          "h-1.5 w-1.5 rounded-full",
          on ? "bg-emerald-300 shadow-[0_0_8px_rgba(52,211,153,0.7)]" : "bg-white/25",
        ].join(" ")}
      />
      <span>{label}</span>
      <Switch on={on} size="sm" />
    </button>
  );
}

export function AutomationTopbar({ state }: Props) {
  return (
    <header className="flex items-center gap-3 border-b border-white/[0.08] bg-[rgba(7,10,18,0.72)] px-3 py-1.5 shadow-[0_1px_0_rgba(255,255,255,0.025),0_8px_22px_-12px_rgba(0,0,0,0.6)] backdrop-blur-md backdrop-saturate-150 sm:px-4">
      {/* Brand */}
      <div className="flex shrink-0 items-center gap-2">
        <div
          aria-hidden
          className="grid h-8 w-8 place-items-center rounded-md bg-gradient-to-br from-cyan-400/25 via-cyan-300/10 to-purple-500/20 shadow-[0_0_14px_rgba(0,170,210,0.22)]"
        >
          <svg viewBox="0 0 16 16" className="h-3.5 w-3.5 text-cyan-100" aria-hidden>
            <path
              fill="currentColor"
              d="M2 3h2v10H2zm10 0h2v10h-2zM5.5 3h2v10h-2zm3 0h2v10h-2z"
            />
          </svg>
        </div>
        <div className="text-[14px] font-semibold tracking-tight text-white">MIDI Mapper</div>
      </div>

      {/* AUTOMATION ARMED — centered cluster */}
      <div className="ml-auto flex items-center gap-2.5">
        <div
          className={[
            "flex !h-8 items-center gap-2.5 rounded-md border !px-2.5 !text-[10px] uppercase tracking-[0.16em]",
            state.armed
              ? "border-emerald-300/30 bg-emerald-400/[0.06] text-emerald-100 shadow-[0_0_22px_-8px_rgba(52,211,153,0.55)]"
              : "border-white/10 bg-white/[0.03] text-white/55",
          ].join(" ")}
        >
          <span className="font-semibold tracking-[0.18em]">Automation Armed</span>
          <span
            className={[
              "rounded px-1.5 py-px text-[9.5px] font-bold tracking-wider",
              state.armed
                ? "bg-emerald-400/20 text-emerald-100"
                : "bg-white/10 text-white/60",
            ].join(" ")}
          >
            {state.armed ? "ON" : "OFF"}
          </span>
          <Switch on={state.armed} size="sm" />
          <span aria-hidden className="text-white/45">
            <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.4">
              <rect x="3.5" y="7" width="9" height="6.5" rx="1.2" />
              <path d="M5.5 7V5.2a2.5 2.5 0 0 1 5 0V7" />
            </svg>
          </span>
        </div>
      </div>

      {/* Right cluster */}
      <div className="flex shrink-0 items-center gap-2">
        <label className="flex !h-8 items-center gap-2 rounded-md border border-white/10 bg-white/[0.03] !px-2.5 !text-[10.5px] text-white/70">
          <span className="uppercase tracking-[0.12em] text-white/50">Matching</span>
          <select
            aria-label="Matching mode"
            className="!h-6 !rounded !border-white/10 !bg-black/40 !px-1.5 !py-0 !text-[11px]"
            value={state.matchingMode}
            onChange={() => undefined}
          >
            <option value="legacy">Legacy</option>
            <option value="v2">V2</option>
            <option value="dual">Dual</option>
          </select>
        </label>

        <ToggleLine label="Mouse Mode" on={state.mouseMode} />
        <ToggleLine label="Live Console" on={state.liveConsole} />

        <button
          type="button"
          className="grid !h-8 !w-8 place-items-center rounded-md border border-white/10 bg-white/[0.03] !p-0 text-white/70 hover:bg-white/[0.06]"
          aria-label="Settings"
          title="Settings"
        >
          <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.4">
            <circle cx="8" cy="8" r="2" />
            <path d="M8 1.5v2M8 12.5v2M14.5 8h-2M3.5 8h-2M12.6 3.4l-1.4 1.4M4.8 11.2l-1.4 1.4M12.6 12.6l-1.4-1.4M4.8 4.8 3.4 3.4" />
          </svg>
        </button>
      </div>
    </header>
  );
}
