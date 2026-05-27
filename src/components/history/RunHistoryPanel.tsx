"use client";

import { useMemo, useState } from "react";
import { ConfirmDialog } from "../ConfirmDialog";
import { groupRunsIntoSessions } from "../v2/adapters";
import type { SessionStatus, V2ExecutionSession, V2RunSummary } from "../v2/types";

type Props = {
  runs: V2RunSummary[];
  onClearRuns?: () => Promise<void>;
};

const SESSION_STATUS_STYLE: Record<SessionStatus, string> = {
  success: "border-emerald-300/25 bg-emerald-400/[0.06] text-emerald-100",
  partial: "border-amber-300/25 bg-amber-400/[0.06] text-amber-100",
  failed: "border-rose-300/25 bg-rose-400/[0.06] text-rose-100",
  error: "border-rose-300/25 bg-rose-400/[0.06] text-rose-100",
  timeout: "border-amber-300/25 bg-amber-400/[0.06] text-amber-100",
};

const STEP_STATUS_DOT: Record<string, string> = {
  success: "bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.55)]",
  failed: "bg-rose-400 shadow-[0_0_4px_rgba(251,113,133,0.55)]",
  error: "bg-rose-400 shadow-[0_0_4px_rgba(251,113,133,0.55)]",
  timeout: "bg-amber-400 shadow-[0_0_4px_rgba(251,191,36,0.55)]",
};

function relativeTime(iso: string | undefined): string {
  if (!iso) return "recently";
  const seconds = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  return `${Math.round(minutes / 60)}h ago`;
}

function StatusPill({ status, label }: { status: SessionStatus; label?: string }) {
  const cls = SESSION_STATUS_STYLE[status] ?? SESSION_STATUS_STYLE.error;
  const text = label ?? (status === "partial" ? "Partial" : status.charAt(0).toUpperCase() + status.slice(1));
  return (
    <span className={`inline-flex items-center rounded border !px-1.5 !py-px text-[9.5px] uppercase tracking-[0.12em] ${cls}`}>
      {text}
    </span>
  );
}

function StepRow({ run, isLast }: { run: V2RunSummary; isLast: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const dotClass = STEP_STATUS_DOT[run.status] ?? "bg-white/20";
  const hasOutput = Boolean(run.stdoutPreview || run.stderrPreview || run.errorMessage);
  const time = run.startedAt
    ? new Date(run.startedAt).toLocaleTimeString(undefined, { hour12: false })
    : undefined;

  return (
    <div className="flex gap-0">
      {/* Tree connector */}
      <div className="flex w-5 shrink-0 flex-col items-center">
        <div className="w-px flex-1 bg-white/[0.08]" />
        {isLast && <div className="h-2.5 w-px bg-transparent" />}
      </div>
      {/* Content */}
      <div className="mb-1 min-w-0 flex-1">
        <button
          type="button"
          disabled={!hasOutput}
          onClick={() => setExpanded((e) => !e)}
          className={[
            "w-full rounded border border-white/[0.06] bg-zinc-900/40 !px-2 !py-1 text-left",
            hasOutput ? "cursor-pointer hover:border-white/15" : "cursor-default",
          ].join(" ")}
        >
          <div className="flex items-center gap-2">
            <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${dotClass}`} />
            <span className="min-w-0 flex-1 truncate font-mono text-[10.5px] text-white/80">
              {run.actionLabel}
            </span>
            <span className="shrink-0 font-mono text-[9.5px] text-white/30">{run.durationMs}ms</span>
            {time && <span className="shrink-0 font-mono text-[9px] text-white/25">{time}</span>}
          </div>
          {expanded && hasOutput && (
            <div className="mt-1 border-t border-white/[0.05] pt-1 font-mono text-[10px]">
              {run.stdoutPreview && (
                <pre className="max-h-20 overflow-y-auto whitespace-pre-wrap break-all text-emerald-200/70">
                  {run.stdoutPreview}
                </pre>
              )}
              {run.stderrPreview && (
                <pre className="max-h-20 overflow-y-auto whitespace-pre-wrap break-all text-rose-200/70">
                  {run.stderrPreview}
                </pre>
              )}
              {run.errorMessage && !run.stderrPreview && (
                <pre className="whitespace-pre-wrap break-all text-amber-200/70">{run.errorMessage}</pre>
              )}
            </div>
          )}
        </button>
      </div>
    </div>
  );
}

function SessionCard({ session }: { session: V2ExecutionSession }) {
  const [expanded, setExpanded] = useState(false);
  const time = relativeTime(session.startedAt);
  const isSingle = session.stepCount === 1 && !session.steps[0]?.sessionId;

  return (
    <div className="rounded-md border border-white/8 bg-zinc-900/50">
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center gap-2 !px-2.5 !py-1.5 text-left hover:bg-white/[0.02]"
      >
        {/* Expand chevron */}
        <svg
          viewBox="0 0 16 16"
          className={`h-2.5 w-2.5 shrink-0 text-white/30 transition-transform ${expanded ? "rotate-90" : ""}`}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
        >
          <path d="M5.5 3.5L10.5 8l-5 4.5" />
        </svg>

        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-1.5">
            <span className="truncate font-mono text-[11.5px] font-semibold text-white">
              {session.triggerLabel}
            </span>
            {session.triggerCondition && (
              <span className="font-mono text-[10px] text-white/35">{session.triggerCondition}</span>
            )}
          </div>
          {!isSingle && (
            <div className="mt-0.5 font-mono text-[9.5px] text-white/30">
              {session.stepCount} step{session.stepCount === 1 ? "" : "s"} · {session.totalDurationMs}ms total
            </div>
          )}
        </div>

        <div className="flex shrink-0 flex-col items-end gap-px">
          <StatusPill status={session.status} />
          <span className="font-mono text-[9.5px] text-white/30">{time}</span>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-white/[0.05] !px-2 !pb-2 !pt-1.5">
          {session.steps.map((step, i) => (
            <StepRow key={step.id} run={step} isLast={i === session.steps.length - 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export function RunHistoryPanel({ runs, onClearRuns }: Props) {
  const [clearOpen, setClearOpen] = useState(false);
  const sessions = useMemo(() => groupRunsIntoSessions(runs), [runs]);

  return (
    <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-4 flex items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-white">Run history</h2>
          <p className="text-xs text-white/45">
            Execution timeline — grouped by trigger session.
          </p>
        </div>
        {runs.length > 0 && onClearRuns && (
          <button
            type="button"
            onClick={() => setClearOpen(true)}
            className="mt-0.5 !h-6 shrink-0 rounded-md border border-white/10 !px-2 !text-[10.5px] text-white/55 hover:text-white/80"
            style={{ background: "rgba(255,255,255,0.03)" }}
          >
            Clear
          </button>
        )}
      </div>

      {sessions.length === 0 ? (
        <p className="py-2 text-center text-[11px] text-white/30">No runs yet</p>
      ) : (
        <div className="space-y-1">
          {sessions.slice(0, 40).map((session) => (
            <SessionCard key={session.sessionId} session={session} />
          ))}
        </div>
      )}

      <ConfirmDialog
        open={clearOpen}
        message="Clear all run history?"
        confirmLabel="Clear"
        onConfirm={() => { setClearOpen(false); void onClearRuns?.(); }}
        onCancel={() => setClearOpen(false)}
      />
    </section>
  );
}
