"use client";

import { useEffect } from "react";
import type { V2RunSummary } from "../v2/types";

type Props = {
  runs: V2RunSummary[];
  onClose: () => void;
  onClearRuns?: () => Promise<void>;
};

const STATUS_DOT: Record<string, string> = {
  success: "bg-emerald-400 shadow-[0_0_5px_rgba(52,211,153,0.6)]",
  failed: "bg-rose-400 shadow-[0_0_5px_rgba(251,113,133,0.6)]",
  error: "bg-rose-400 shadow-[0_0_5px_rgba(251,113,133,0.6)]",
  timeout: "bg-amber-400 shadow-[0_0_5px_rgba(251,191,36,0.6)]",
};

export function ConsolePanel({ runs, onClose, onClearRuns }: Props) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-x-0 bottom-0 z-40 flex flex-col border-t border-white/15 bg-zinc-950 shadow-[0_-8px_40px_rgba(0,0,0,0.7)]">
      {/* Header bar */}
      <div className="flex shrink-0 items-center justify-between border-b border-white/8 px-3 py-1.5">
        <div className="flex items-center gap-2">
          <svg viewBox="0 0 16 16" className="h-3 w-3 text-white/40" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="2.5" y="3" width="11" height="10" rx="1.2" />
            <path d="M5 7l1.5 1.5L5 10M8.5 10h2.5" />
          </svg>
          <span className="text-[9.5px] font-semibold uppercase tracking-[0.18em] text-white/45">
            Console — Run Output
          </span>
          {runs.length > 0 && (
            <span className="rounded bg-white/[0.06] !px-1 font-mono text-[9px] text-white/40">
              {runs.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {runs.length > 0 && onClearRuns && (
            <button
              type="button"
              onClick={() => void onClearRuns()}
              className="text-[10px] text-white/35 hover:text-white/60"
              style={{ background: "transparent", border: "none", padding: 0 }}
            >
              Clear
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            aria-label="Close console"
            className="grid h-4 w-4 place-items-center text-white/35 hover:text-white/70"
            style={{ background: "transparent", border: "none", padding: 0 }}
          >
            <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path d="M3 3l10 10M13 3L3 13" />
            </svg>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="h-[220px] overflow-y-auto font-mono text-[11px]">
        {runs.length === 0 ? (
          <p className="p-3 text-white/30">
            No runs yet. Trigger a binding or use Test Action.
          </p>
        ) : (
          <div className="divide-y divide-white/[0.04]">
            {runs.slice(0, 30).map((run) => (
              <ConsoleLine key={run.id} run={run} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ConsoleLine({ run }: { run: V2RunSummary }) {
  const dotClass = STATUS_DOT[run.status] ?? "bg-white/30";
  const time = run.startedAt
    ? new Date(run.startedAt).toLocaleTimeString(undefined, { hour12: false })
    : run.relativeTime;

  return (
    <div className="px-3 py-1.5">
      <div className="flex items-center gap-2">
        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${dotClass}`} />
        <span className="text-white/35">{time}</span>
        <span className="min-w-0 flex-1 truncate text-white/80">{run.actionLabel}</span>
        {run.durationMs != null && (
          <span className="shrink-0 text-white/30">{run.durationMs}ms</span>
        )}
        {run.statusDetail && (
          <span className={[
            "shrink-0 text-[10px]",
            run.status === "success" ? "text-emerald-300/60" : "text-rose-300/60",
          ].join(" ")}>
            exit {run.statusDetail}
          </span>
        )}
      </div>
      {run.stdoutPreview && (
        <pre className="mt-0.5 max-h-16 overflow-y-auto whitespace-pre-wrap break-all pl-5 text-emerald-200/65">
          {run.stdoutPreview}
        </pre>
      )}
      {run.stderrPreview && (
        <pre className="mt-0.5 max-h-16 overflow-y-auto whitespace-pre-wrap break-all pl-5 text-rose-200/65">
          {run.stderrPreview}
        </pre>
      )}
      {run.errorMessage && !run.stderrPreview && run.status !== "success" && (
        <pre className="mt-0.5 whitespace-pre-wrap break-all pl-5 text-amber-200/65">
          {run.errorMessage}
        </pre>
      )}
    </div>
  );
}
