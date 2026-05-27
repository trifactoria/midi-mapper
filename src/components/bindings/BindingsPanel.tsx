import type { V2BindingSummary } from "../v2/types";
import { ActiveBindingsList } from "./ActiveBindingsList";

type Props = {
  bindings: V2BindingSummary[];
};

export function BindingsPanel({ bindings }: Props) {
  return (
    <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-4">
        <h2 className="text-base font-semibold text-white">Bindings</h2>
        <p className="text-xs text-white/45">All bindings in the active layer. Use the Mapping tab to create or edit bindings.</p>
      </div>
      {bindings.length === 0 ? (
        <p className="text-[11px] text-white/30">No bindings yet — add one from the Mapping tab.</p>
      ) : (
        <ActiveBindingsList bindings={bindings} />
      )}
    </section>
  );
}
