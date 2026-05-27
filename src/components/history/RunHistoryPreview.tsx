"use client";

import { useState } from "react";
import type { V2RunSummary } from "../v2/types";

type Props = {
  runs: V2RunSummary[];
};

function statusPill(run: V2RunSummary) {
  const label = run.status === "success" ? "Success" : run.status === "failed" ? "Failed" : run.status;
  const cls =
    run.status === "success"
      ? "border-emerald-300/25 bg-emerald-400/[0.06] text-emerald-100"
      : run.status === "failed" || run.status === "error"
      ? "border-rose-300/25 bg-rose-400/[0.06] text-rose-100"
      : "border-amber-300/25 bg-amber-400/[0.06] text-amber-100";
  const detail = run.statusDetail ? ` (${run.statusDetail})` : "";
  return (
    <span
      className={[
        "inline-flex items-center gap-1 rounded border !px-1.5 !py-px text-[9.5px] uppercase tracking-[0.12em]",
        cls,
      ].join(" ")}
    >
      {label}
      {detail}
    </span>
  );
}

function RunDetail({ run }: { run: V2RunSummary }) {
  const hasOutput = run.stdoutPreview || run.stderrPreview || run.errorMessage;
  if (!hasOutput && run.durationMs == null) return null;

  return (
    <div className="mt-1.5 border-t border-white/[0.05] pt-1.5 font-mono text-[10px]">
      <div className="flex items-center gap-3 text-white/35">
        {typeof run.durationMs === "number" && (
          <span>{run.durationMs}ms</span>
        )}
        {run.startedAt && (
          <span>{new Date(run.startedAt).toLocaleTimeString()}</span>
        )}
      </div>
      {run.stdoutPreview && (
        <pre className="mt-1 max-h-20 overflow-y-auto whitespace-pre-wrap break-all text-emerald-200/70">
          {run.stdoutPreview}
        </pre>
      )}
      {run.stderrPreview && (
        <pre className="mt-1 max-h-20 overflow-y-auto whitespace-pre-wrap break-all text-rose-200/70">
          {run.stderrPreview}
        </pre>
      )}
      {run.errorMessage && !run.stderrPreview && (
        <pre className="mt-1 whitespace-pre-wrap break-all text-amber-200/70">
          {run.errorMessage}
        </pre>
      )}
    </div>
  );
}

export function RunHistoryPreview({ runs }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (runs.length === 0) {
    return (
      <p className="py-2 text-center text-[11px] text-white/30">No runs yet</p>
    );
  }

  return (
    <div className="space-y-1">
      {runs.map((run) => {
        const expanded = expandedId === run.id;
        const hasDetail = Boolean(run.stdoutPreview || run.stderrPreview || run.errorMessage || run.durationMs);
        return (
          <div
            key={run.id}
            onClick={() => hasDetail && setExpandedId(expanded ? null : run.id)}
            className={[
              "rounded-md border border-white/8 bg-zinc-900/50 !px-2 !py-1 transition",
              hasDetail ? "cursor-pointer hover:border-white/15" : "",
            ].join(" ")}
          >
            <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2">
              <span
                className="grid h-4 w-4 place-items-center rounded-full bg-white/[0.05] text-white/70"
                aria-hidden
              >
                <svg viewBox="0 0 16 16" className="h-2 w-2" fill="currentColor">
                  <path d="M5 3.5l7 4.5-7 4.5V3.5z" />
                </svg>
              </span>

              <div className="min-w-0 leading-tight">
                <div className="flex items-center gap-1.5">
                  <span className="truncate font-mono text-[11.5px] font-semibold text-white">
                    {run.triggerLabel}
                  </span>
                  {run.triggerCondition && (
                    <span className="font-mono text-[10px] text-white/40">{run.triggerCondition}</span>
                  )}
                </div>
                <div className="mt-0.5 truncate font-mono text-[10px] text-white/50">{run.actionLabel}</div>
              </div>

              <div className="flex shrink-0 flex-col items-end gap-px">
                {statusPill(run)}
                <span className="text-[9.5px] text-white/35">{run.relativeTime}</span>
              </div>
            </div>

            {expanded && <RunDetail run={run} />}
          </div>
        );
      })}
    </div>
  );
}
