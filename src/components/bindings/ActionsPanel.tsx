import type { V2BindingSummary } from "../v2/types";

type Props = {
  bindings: V2BindingSummary[];
};

export function ActionsPanel({ bindings }: Props) {
  return (
    <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-4">
        <h2 className="text-base font-semibold text-white">Actions</h2>
        <p className="text-xs text-white/45">Command actions that bindings can run.</p>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {bindings.map((binding) => (
          <div key={binding.id} className="rounded-md border border-white/10 bg-black/20 p-3">
            <div className="text-sm font-semibold text-white">{binding.label}</div>
            <code className="mt-2 block rounded bg-black/45 px-2 py-2 text-xs text-cyan-100">{binding.action}</code>
            <div className="mt-2 text-xs text-white/45">{binding.trigger}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

