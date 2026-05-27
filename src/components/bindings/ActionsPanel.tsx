import type { V2BindingSummary } from "../v2/types";

type Props = {
  bindings: V2BindingSummary[];
};

const BINDING_COLOR_HEX: Record<string, string> = {
  cyan: "#22d3ee",
  emerald: "#34d399",
  violet: "#a78bfa",
  amber: "#fbbf24",
  rose: "#fb7185",
  blue: "#60a5fa",
  slate: "#94a3b8",
  purple: "#c084fc",
  orange: "#fb923c",
  red: "#f87171",
};

function bindingColorHex(color: string | undefined): string | undefined {
  if (!color) return undefined;
  if (color.startsWith("#")) return color;
  return BINDING_COLOR_HEX[color];
}

export function ActionsPanel({ bindings }: Props) {
  const commandCount = bindings.filter((binding) => Boolean(binding.command)).length;
  const enabledCount = bindings.filter((binding) => binding.enabled).length;

  return (
    <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-white">Actions</h2>
          <p className="text-xs text-white/45">Commands attached to active-layer bindings. Sequencing is not shown here yet.</p>
        </div>
        <div className="flex shrink-0 gap-1.5 font-mono text-[10px] text-white/45">
          <span className="rounded border border-white/10 bg-white/[0.04] px-1.5 py-px">{commandCount} commands</span>
          <span className="rounded border border-emerald-300/15 bg-emerald-300/[0.05] px-1.5 py-px">{enabledCount} enabled</span>
        </div>
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
                {binding.displayColor && bindingColorHex(binding.displayColor) && (
                  <span
                    className="mt-0.5 h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: bindingColorHex(binding.displayColor) }}
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
