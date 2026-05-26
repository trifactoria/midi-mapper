"use client";

import { useState } from "react";
import { ConfirmDialog } from "../ConfirmDialog";
import type { V2RunSummary } from "../v2/types";
import { RunHistoryPreview } from "./RunHistoryPreview";

type Props = {
  runs: V2RunSummary[];
  onClearRuns?: () => Promise<void>;
};

export function RunHistoryPanel({ runs, onClearRuns }: Props) {
  const [clearOpen, setClearOpen] = useState(false);

  return (
    <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-4 flex items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-white">Run history</h2>
          <p className="text-xs text-white/45">Recent action test and execution records.</p>
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
      <RunHistoryPreview runs={runs} />
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

