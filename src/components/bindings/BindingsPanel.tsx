import type { V2BindingSummary } from "../v2/types";
import { ActiveBindingsList } from "./ActiveBindingsList";

type Props = {
  bindings: V2BindingSummary[];
};

export function BindingsPanel({ bindings }: Props) {
  const noteCount = bindings.filter((binding) => binding.kind === "note").length;
  const ccCount = bindings.filter((binding) => binding.kind === "cc").length;

  return (
    <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-white">Bindings</h2>
          <p className="text-xs text-white/45">All note and CC bindings in the active layer. Use Mapping to create or edit them.</p>
        </div>
        <div className="flex shrink-0 gap-1.5 font-mono text-[10px] text-white/45">
          <span className="rounded border border-white/10 bg-white/[0.04] px-1.5 py-px">{bindings.length} total</span>
          <span className="rounded border border-cyan-300/15 bg-cyan-300/[0.05] px-1.5 py-px">{noteCount} note</span>
          <span className="rounded border border-amber-300/15 bg-amber-300/[0.05] px-1.5 py-px">{ccCount} CC</span>
        </div>
      </div>
      {bindings.length === 0 ? (
        <p className="text-[11px] text-white/30">No bindings yet — add one from the Mapping tab.</p>
      ) : (
        <ActiveBindingsList bindings={bindings} />
      )}
    </section>
  );
}
