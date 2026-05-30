import type { V2BindingSummary } from "../v2/types";
import { ActiveBindingsList } from "./ActiveBindingsList";

type Props = {
  bindings: V2BindingSummary[];
};

export function BindingsPanel({ bindings }: Props) {
  const noteCount = bindings.filter((b) => b.kind === "note").length;
  const ccCount = bindings.filter((b) => b.kind === "cc").length;

  return (
    <section className="rounded-md border border-white/8 bg-white/[0.014] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.018),inset_0_0_24px_rgba(0,0,0,0.18)]">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/65">
          Bindings
          <span className="rounded bg-white/[0.06] !px-1 !py-px font-mono text-[10px] text-white/60">
            {bindings.length}
          </span>
        </h3>
        <div className="flex shrink-0 items-center gap-1 font-mono text-[10px]">
          <span className="rounded border border-cyan-300/15 bg-cyan-300/[0.05] px-1.5 py-px text-cyan-200/60">
            {noteCount} note
          </span>
          <span className="rounded border border-amber-300/15 bg-amber-300/[0.05] px-1.5 py-px text-amber-200/60">
            {ccCount} CC
          </span>
        </div>
      </div>
      {bindings.length === 0 ? (
        <p className="py-4 text-center text-[11px] text-white/30">
          No bindings yet — create one from the Mapping tab.
        </p>
      ) : (
        <ActiveBindingsList bindings={bindings} />
      )}
    </section>
  );
}
