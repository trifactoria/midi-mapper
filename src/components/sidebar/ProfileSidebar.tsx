import type { V2LayerSummary, V2ProfileSummary } from "../v2/types";

type Props = {
  profiles: V2ProfileSummary[];
  layers: V2LayerSummary[];
};

function PlusButton({ label }: { label: string }) {
  return (
    <button
      type="button"
      className="grid !h-5 !w-5 place-items-center rounded border border-white/10 bg-white/[0.04] !p-0 text-white/70 hover:bg-white/[0.08]"
      aria-label={label}
      title={label}
    >
      <svg viewBox="0 0 16 16" className="h-2.5 w-2.5" fill="none" stroke="currentColor" strokeWidth="1.6">
        <path d="M8 3v10M3 8h10" />
      </svg>
    </button>
  );
}

function StarIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="currentColor">
      <path d="M8 1.5l1.95 4.13 4.55.55-3.36 3.13.83 4.49L8 11.7l-3.97 2.1.83-4.49L1.5 6.18l4.55-.55L8 1.5z" />
    </svg>
  );
}

export function ProfileSidebar({ profiles, layers }: Props) {
  return (
    <aside className="flex h-full min-h-0 flex-col border-r border-white/10 bg-black/55 shadow-[inset_-8px_0_24px_-12px_rgba(0,0,0,0.6)]">
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-2.5">
        <section>
          <div className="mb-1.5 flex items-center justify-between px-1">
            <h2 className="text-[9.5px] font-semibold uppercase tracking-[0.18em] text-white/45">
              Profiles
            </h2>
            <PlusButton label="New profile" />
          </div>
          <div className="space-y-px">
            {profiles.map((profile) => (
              <button
                type="button"
                key={profile.id}
                className={[
                  "group flex w-full items-center gap-2 rounded !px-2 !py-1 text-left transition",
                  profile.active
                    ? "bg-cyan-300/[0.06] text-white shadow-[inset_0_0_0_1px_rgba(0,180,210,0.18)]"
                    : "text-white/70 hover:bg-white/[0.04] hover:text-white/90",
                ].join(" ")}
              >
                <span
                  className={[
                    "h-1.5 w-1.5 shrink-0 rounded-full",
                    profile.active
                      ? "bg-cyan-300 shadow-[0_0_7px_rgba(0,180,210,0.6)]"
                      : "bg-white/20",
                  ].join(" ")}
                />
                <span className="min-w-0 flex-1 truncate text-[12px] font-medium">
                  {profile.name}
                </span>
                {profile.starred && (
                  <span className="text-amber-300/90" aria-label="favorite">
                    <StarIcon />
                  </span>
                )}
              </button>
            ))}
          </div>
        </section>

        <section>
          <div className="mb-1.5 flex items-center justify-between px-1">
            <h2 className="text-[9.5px] font-semibold uppercase tracking-[0.18em] text-white/45">
              Layers
            </h2>
            <PlusButton label="New layer" />
          </div>
          <div className="space-y-px">
            {layers.map((layer) => (
              <button
                type="button"
                key={layer.id}
                className={[
                  "group flex w-full items-center gap-2 rounded !px-2 !py-1 text-left transition",
                  layer.active
                    ? "bg-white/[0.06] text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.10)]"
                    : "text-white/70 hover:bg-white/[0.04] hover:text-white/90",
                ].join(" ")}
              >
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{
                    backgroundColor: layer.color,
                    boxShadow: layer.active ? `0 0 10px ${layer.color}` : "none",
                  }}
                />
                <span className="min-w-0 flex-1 truncate text-[12px] font-medium">
                  {layer.name}
                </span>
                <span className="shrink-0 font-mono text-[10px] tabular-nums text-white/35">
                  {layer.bindingCount}
                </span>
              </button>
            ))}
          </div>
        </section>
      </div>

      <div className="space-y-1.5 border-t border-white/10 px-2.5 py-2.5">
        <button
          type="button"
          className="flex w-full items-center gap-2 rounded-md border border-white/10 bg-white/[0.03] !px-2 !py-1.5 text-left !text-[12px] text-white/75 hover:bg-white/[0.06]"
        >
          <svg viewBox="0 0 16 16" className="h-3 w-3 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.4">
            <path d="M8 2.5v8m0 0l-2.5-2.5M8 10.5l2.5-2.5M3 13.5h10" />
          </svg>
          Import / Export
        </button>
        <div className="px-1 text-[9.5px] uppercase tracking-[0.18em] text-white/30">v0.2.0</div>
      </div>
    </aside>
  );
}

// Compact horizontal selectors for mobile. Active profile/layer become dropdowns.
export function ProfileLayerCompactBar({ profiles, layers }: Props) {
  const activeProfile = profiles.find((p) => p.active) ?? profiles[0];
  const activeLayer = layers.find((l) => l.active) ?? layers[0];

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
      <label className="flex min-w-0 flex-1 items-center gap-2 rounded-md border border-white/10 bg-white/[0.04] px-3 py-2">
        <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/40">
          Profile
        </span>
        <select
          aria-label="Active profile"
          className="min-w-0 flex-1 truncate border-none bg-transparent p-0 text-sm text-white focus:ring-0"
          defaultValue={activeProfile.id}
        >
          {profiles.map((profile) => (
            <option key={profile.id} value={profile.id} className="bg-zinc-900">
              {profile.name}
            </option>
          ))}
        </select>
      </label>

      <label className="flex min-w-0 flex-1 items-center gap-2 rounded-md border border-white/10 bg-white/[0.04] px-3 py-2">
        <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/40">
          Layer
        </span>
        <span
          className="h-2.5 w-2.5 shrink-0 rounded-full"
          style={{ backgroundColor: activeLayer.color, boxShadow: `0 0 10px ${activeLayer.color}` }}
        />
        <select
          aria-label="Active layer"
          className="min-w-0 flex-1 truncate border-none bg-transparent p-0 text-sm text-white focus:ring-0"
          defaultValue={activeLayer.id}
        >
          {layers.map((layer) => (
            <option key={layer.id} value={layer.id} className="bg-zinc-900">
              {layer.name}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
