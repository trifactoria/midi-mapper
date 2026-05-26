import type { V2RunSummary } from "../v2/types";
import { RunHistoryPreview } from "./RunHistoryPreview";

type Props = {
  runs: V2RunSummary[];
};

export function RunHistoryPanel({ runs }: Props) {
  return (
    <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-4">
        <h2 className="text-base font-semibold text-white">Run history</h2>
        <p className="text-xs text-white/45">Recent action test and execution records.</p>
      </div>
      <RunHistoryPreview runs={runs} />
    </section>
  );
}

