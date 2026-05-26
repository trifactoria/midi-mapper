import type { V2BindingSummary } from "../v2/types";
import { ActiveBindingsList } from "./ActiveBindingsList";

type Props = {
  bindings: V2BindingSummary[];
};

export function BindingsPanel({ bindings }: Props) {
  return (
    <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-white">Bindings</h2>
          <p className="text-xs text-white/45">Current v2 binding list mockup.</p>
        </div>
        <button type="button" className="rounded-md text-sm">New Binding</button>
      </div>
      <ActiveBindingsList bindings={bindings} />
    </section>
  );
}

