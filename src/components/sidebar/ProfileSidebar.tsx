import { useState } from "react";
import { ConfirmDialog } from "../ConfirmDialog";
import type { V2LayerSummary, V2ProfileSummary } from "../v2/types";

type Props = {
  profiles: V2ProfileSummary[];
  layers: V2LayerSummary[];
  onProfileActivate?: (profileId: string) => void;
  onLayerActivate?: (layerId: string) => void;
  onCreateProfile?: () => Promise<string | null>;
  onCreateLayer?: () => Promise<string | null>;
  onRenameProfile?: (profileId: string, name: string) => Promise<void>;
  onRenameLayer?: (layerId: string, name: string) => Promise<void>;
  onDeleteProfile?: (profileId: string) => Promise<void>;
  onDeleteLayer?: (layerId: string) => Promise<void>;
};

type EditTarget = { type: "profile" | "layer"; id: string; draft: string } | null;
type DeleteTarget = { type: "profile" | "layer"; id: string; name: string } | null;

function PlusButton({
  label,
  onClick,
  disabled,
}: {
  label: string;
  onClick?: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={[
        "grid !h-5 !w-5 place-items-center rounded border !p-0",
        disabled
          ? "cursor-not-allowed border-white/5 bg-white/[0.02] text-white/20"
          : "border-white/10 bg-white/[0.04] text-white/70 hover:bg-white/[0.08]",
      ].join(" ")}
      aria-label={label}
      title={disabled ? "Create a profile first" : label}
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

export function ProfileSidebar({
  profiles,
  layers,
  onProfileActivate,
  onLayerActivate,
  onCreateProfile,
  onCreateLayer,
  onRenameProfile,
  onRenameLayer,
  onDeleteProfile,
  onDeleteLayer,
}: Props) {
  const [editing, setEditing] = useState<EditTarget>(null);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  function startEdit(type: "profile" | "layer", id: string, currentName: string) {
    setEditing({ type, id, draft: currentName });
  }

  function cancelEdit() {
    setEditing(null);
  }

  async function commitRename() {
    if (!editing) return;
    const { type, id, draft } = editing;
    const name = draft.trim();
    setEditing(null);
    if (!name) return;
    if (type === "profile") {
      await onRenameProfile?.(id, name);
    } else {
      await onRenameLayer?.(id, name);
    }
  }

  async function handleCreateProfile() {
    const newId = await onCreateProfile?.();
    if (newId) startEdit("profile", newId, "New Profile");
  }

  async function handleCreateLayer() {
    const newId = await onCreateLayer?.();
    if (newId) startEdit("layer", newId, "New Layer");
  }

  const rowBase = "group flex w-full items-center gap-2 rounded !px-2 !py-1 text-left transition";
  const rowActive = "bg-cyan-300/[0.06] text-white shadow-[inset_0_0_0_1px_rgba(0,180,210,0.18)]";
  const rowInactive = "text-white/70 hover:bg-white/[0.04] hover:text-white/90";
  const layerRowActive = "bg-white/[0.06] text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.10)]";

  return (
    <aside className="flex h-full min-h-0 flex-col border-r border-white/10 bg-black/55 shadow-[inset_-8px_0_24px_-12px_rgba(0,0,0,0.6)]">
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-2.5">
        {/* Profiles section */}
        <section>
          <div className="mb-1.5 flex items-center justify-between px-1">
            <h2 className="text-[9.5px] font-semibold uppercase tracking-[0.18em] text-white/45">
              Profiles
            </h2>
            <PlusButton label="New profile" onClick={() => void handleCreateProfile()} />
          </div>
          <div className="space-y-px">
            {profiles.length === 0 && (
              <p className="px-1 py-1.5 text-[11px] text-white/30">No profiles</p>
            )}
            {profiles.map((profile) =>
              editing?.type === "profile" && editing.id === profile.id ? (
                <div key={profile.id} className={[rowBase, rowActive].join(" ")}>
                  <span
                    className={[
                      "h-1.5 w-1.5 shrink-0 rounded-full",
                      "bg-cyan-300 shadow-[0_0_7px_rgba(0,180,210,0.6)]",
                    ].join(" ")}
                  />
                  <input
                    autoFocus
                    className="min-w-0 flex-1 bg-transparent text-[12px] font-medium text-white focus:outline-none"
                    value={editing.draft}
                    onChange={(e) => setEditing({ ...editing, draft: e.target.value })}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") { e.preventDefault(); void commitRename(); }
                      if (e.key === "Escape") { e.preventDefault(); cancelEdit(); }
                    }}
                    onBlur={() => void commitRename()}
                  />
                </div>
              ) : (
                <div
                  key={profile.id}
                  className={[rowBase, profile.active ? rowActive : rowInactive].join(" ")}
                  role="button"
                  tabIndex={0}
                  onClick={() => onProfileActivate?.(profile.id)}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onProfileActivate?.(profile.id); }}
                >
                  <span
                    className={[
                      "h-1.5 w-1.5 shrink-0 rounded-full",
                      profile.active
                        ? "bg-cyan-300 shadow-[0_0_7px_rgba(0,180,210,0.6)]"
                        : "bg-white/20",
                    ].join(" ")}
                  />
                  <span
                    className="min-w-0 flex-1 truncate text-[12px] font-medium"
                    onDoubleClick={(e) => { e.stopPropagation(); startEdit("profile", profile.id, profile.name); }}
                  >
                    {profile.name}
                  </span>
                  {profile.starred && (
                    <span className="text-amber-300/90" aria-label="favorite">
                      <StarIcon />
                    </span>
                  )}
                  {onDeleteProfile && profiles.length > 1 && (
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setDeleteTarget({ type: "profile", id: profile.id, name: profile.name }); }}
                      className="ml-auto !h-4 !w-4 shrink-0 place-items-center rounded !p-0 text-white/0 opacity-0 transition group-hover:text-white/40 group-hover:opacity-100 hover:!text-rose-300/80"
                      style={{ background: "transparent", border: "none", display: "grid" }}
                      aria-label={`Delete profile ${profile.name}`}
                      title={`Delete ${profile.name}`}
                    >
                      <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M4 4l8 8M12 4l-8 8" />
                      </svg>
                    </button>
                  )}
                </div>
              ),
            )}
          </div>
        </section>

        {/* Layers section */}
        <section>
          <div className="mb-1.5 flex items-center justify-between px-1">
            <h2 className="text-[9.5px] font-semibold uppercase tracking-[0.18em] text-white/45">
              Layers
            </h2>
            <PlusButton
              label="New layer"
              onClick={() => void handleCreateLayer()}
              disabled={profiles.length === 0}
            />
          </div>
          <div className="space-y-px">
            {layers.length === 0 && (
              <p className="px-1 py-1.5 text-[11px] text-white/30">No layers</p>
            )}
            {layers.map((layer) =>
              editing?.type === "layer" && editing.id === layer.id ? (
                <div key={layer.id} className={[rowBase, layerRowActive].join(" ")}>
                  <span
                    className="h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{ backgroundColor: layer.color ?? "#00d4ff", boxShadow: `0 0 10px ${layer.color ?? "#00d4ff"}` }}
                  />
                  <input
                    autoFocus
                    className="min-w-0 flex-1 bg-transparent text-[12px] font-medium text-white focus:outline-none"
                    value={editing.draft}
                    onChange={(e) => setEditing({ ...editing, draft: e.target.value })}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") { e.preventDefault(); void commitRename(); }
                      if (e.key === "Escape") { e.preventDefault(); cancelEdit(); }
                    }}
                    onBlur={() => void commitRename()}
                  />
                </div>
              ) : (
                <div
                  key={layer.id}
                  className={[rowBase, layer.active ? layerRowActive : rowInactive].join(" ")}
                  role="button"
                  tabIndex={0}
                  onClick={() => onLayerActivate?.(layer.id)}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onLayerActivate?.(layer.id); }}
                >
                  <span
                    className="h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{
                      backgroundColor: layer.color ?? "#00d4ff",
                      boxShadow: layer.active ? `0 0 10px ${layer.color ?? "#00d4ff"}` : "none",
                    }}
                  />
                  <span
                    className="min-w-0 flex-1 truncate text-[12px] font-medium"
                    onDoubleClick={(e) => { e.stopPropagation(); startEdit("layer", layer.id, layer.name); }}
                  >
                    {layer.name}
                  </span>
                  <span className="shrink-0 font-mono text-[10px] tabular-nums text-white/35">
                    {layer.bindingCount}
                  </span>
                  {onDeleteLayer && layers.length > 1 && (
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setDeleteTarget({ type: "layer", id: layer.id, name: layer.name }); }}
                      className="!h-4 !w-4 shrink-0 place-items-center rounded !p-0 text-white/0 opacity-0 transition group-hover:text-white/40 group-hover:opacity-100 hover:!text-rose-300/80"
                      style={{ background: "transparent", border: "none", display: "grid" }}
                      aria-label={`Delete layer ${layer.name}`}
                      title={`Delete ${layer.name}`}
                    >
                      <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M4 4l8 8M12 4l-8 8" />
                      </svg>
                    </button>
                  )}
                </div>
              ),
            )}
          </div>
        </section>
      </div>

      {deleteError && (
        <div className="flex items-start gap-1.5 border-t border-rose-300/15 bg-rose-400/[0.07] px-2.5 py-2">
          <span className="mt-px shrink-0 text-rose-300/80">
            <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="8" cy="8" r="6" />
              <path d="M8 5v3.5M8 10.5v.5" />
            </svg>
          </span>
          <span className="text-[10.5px] leading-tight text-rose-200/80">{deleteError}</span>
          <button
            type="button"
            onClick={() => setDeleteError(null)}
            className="ml-auto shrink-0 !p-0 text-rose-300/50 hover:text-rose-300/80"
            style={{ background: "none", border: "none" }}
            aria-label="Dismiss"
          >
            <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M4 4l8 8M12 4l-8 8" />
            </svg>
          </button>
        </div>
      )}
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

      <ConfirmDialog
        open={deleteTarget !== null}
        message={
          deleteTarget
            ? deleteTarget.type === "profile"
              ? `Delete profile "${deleteTarget.name}"? All its layers and bindings will be removed.`
              : `Delete layer "${deleteTarget.name}"? All its bindings will be removed.`
            : ""
        }
        confirmLabel="Delete"
        onConfirm={() => {
          if (!deleteTarget) return;
          const target = deleteTarget;
          setDeleteTarget(null);
          setDeleteError(null);
          const handler = target.type === "profile" ? onDeleteProfile : onDeleteLayer;
          handler?.(target.id).catch((err: unknown) => {
            const msg = err instanceof Error ? err.message : "Delete failed";
            setDeleteError(msg);
          });
        }}
        onCancel={() => setDeleteTarget(null)}
      />
    </aside>
  );
}

// Compact horizontal selectors for mobile. Active profile/layer become dropdowns.
export function ProfileLayerCompactBar({ profiles, layers, onProfileActivate, onLayerActivate }: Props) {
  const activeProfile = profiles.find((p) => p.active) ?? profiles[0];
  const activeLayer = layers.find((l) => l.active) ?? layers[0];

  if (!activeProfile && !activeLayer && profiles.length === 0 && layers.length === 0) {
    return (
      <p className="text-[11px] text-white/35">No profiles or layers — check backend or create one via sidebar.</p>
    );
  }

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
      <label className="flex min-w-0 flex-1 items-center gap-2 rounded-md border border-white/10 bg-white/[0.04] px-3 py-2">
        <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/40">
          Profile
        </span>
        <select
          aria-label="Active profile"
          className="min-w-0 flex-1 truncate border-none bg-transparent p-0 text-sm text-white focus:ring-0"
          value={activeProfile?.id ?? ""}
          onChange={(event) => onProfileActivate?.(event.target.value)}
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
        {activeLayer && (
          <span
            className="h-2.5 w-2.5 shrink-0 rounded-full"
            style={{ backgroundColor: activeLayer.color, boxShadow: `0 0 10px ${activeLayer.color}` }}
          />
        )}
        <select
          aria-label="Active layer"
          className="min-w-0 flex-1 truncate border-none bg-transparent p-0 text-sm text-white focus:ring-0"
          value={activeLayer?.id ?? ""}
          onChange={(event) => onLayerActivate?.(event.target.value)}
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
