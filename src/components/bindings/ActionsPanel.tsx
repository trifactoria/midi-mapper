import type { V2BindingSummary } from "../v2/types";

type Props = {
  bindings: V2BindingSummary[];
};

export function ActionsPanel({ bindings }: Props) {
  return (
    <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-4">
        <h2 className="text-base font-semibold text-white">Actions</h2>
        <p className="text-xs text-white/45">Command actions attached to bindings in the active layer.</p>
      </div>
      {bindings.length === 0 ? (
        <p className="text-[11px] text-white/30">No actions yet — add bindings from the Mapping tab.</p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {bindings.map((binding) => (
            <div key={binding.id} className="rounded-md border border-white/10 bg-black/20 p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-white">{binding.actionLabel}</div>
                  <div className="mt-0.5 text-[10px] uppercase tracking-[0.10em] text-white/40">
                    {binding.triggerLabel}
                    {binding.triggerCondition ? ` · ${binding.triggerCondition}` : ""}
                  </div>
                </div>
                {binding.displayColor && (
                  <span
                    className="mt-0.5 h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: binding.displayColor }}
                  />
                )}
              </div>
              <code className="mt-2 block truncate rounded bg-black/45 px-2 py-1.5 text-xs text-cyan-100">
                {binding.command}
              </code>
              <div className="mt-1.5 flex flex-wrap gap-2 text-[10px] text-white/35">
                {binding.executionMode && (
                  <span className="rounded bg-white/[0.04] px-1.5 py-px">{binding.executionMode}</span>
                )}
                {binding.workingDirectory && (
                  <span className="truncate font-mono">{binding.workingDirectory}</span>
                )}
                {!binding.enabled && (
                  <span className="rounded bg-white/[0.04] px-1.5 py-px text-amber-300/60">disabled</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
