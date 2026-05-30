"use client";

import { useEffect, useState } from "react";
import { ICONS } from "../icons";
import type { V2BindingSummary } from "../v2/types";

const BINDING_COLOR_HEX: Record<string, string> = {
  cyan:    "#22d3ee",
  emerald: "#34d399",
  violet:  "#a78bfa",
  amber:   "#fbbf24",
  rose:    "#fb7185",
  blue:    "#60a5fa",
  slate:   "#94a3b8",
  purple:  "#c084fc",
  orange:  "#fb923c",
  red:     "#f87171",
};

function bindingColorHex(color: string | undefined): string | undefined {
  if (!color) return undefined;
  if (color.startsWith("#")) return color;
  return BINDING_COLOR_HEX[color];
}

type Props = {
  bindings: V2BindingSummary[];
  compact?: boolean;
  selectedBindingId?: string | null;
  onSelectBinding?: (binding: V2BindingSummary) => void;
  onEditBinding?: (binding: V2BindingSummary) => void;
  onToggleEnabled?: (binding: V2BindingSummary) => void;
  onDuplicateBinding?: (binding: V2BindingSummary) => void;
  onDeleteBinding?: (binding: V2BindingSummary) => void;
};

function KindBadge({ kind }: { kind: V2BindingSummary["kind"] }) {
  if (kind === "cc") {
    return (
      <span className="inline-flex !h-4 items-center rounded border border-amber-300/25 bg-amber-300/[0.08] !px-1 font-mono text-[9.5px] uppercase tracking-[0.12em] text-amber-200">
        CC
      </span>
    );
  }
  return (
    <span className="inline-flex !h-4 items-center rounded border border-cyan-300/25 bg-cyan-300/[0.08] !px-1 font-mono text-[9.5px] uppercase tracking-[0.12em] text-cyan-200">
      Note
    </span>
  );
}

function InlineBindingIcon({ binding }: { binding: V2BindingSummary }) {
  const color = bindingColorHex(binding.displayColor);
  const entry = binding.icon ? ICONS.find((icon) => icon.key === binding.icon) : undefined;
  if (!entry) return null;

  return (
    <span
      className="inline-grid h-4 w-4 shrink-0 place-items-center"
      style={{ color: color ?? "#67e8f9" }}
      title={entry.label}
    >
      <svg
        viewBox="0 0 24 24"
        className="h-3.5 w-3.5"
        fill={entry.fill ? "currentColor" : "none"}
        stroke={entry.fill ? "none" : "currentColor"}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {entry.paths.map((d, i) => (
          <path key={i} d={d} />
        ))}
      </svg>
    </span>
  );
}

export function ActiveBindingsList({
  bindings,
  compact = false,
  selectedBindingId,
  onSelectBinding,
  onEditBinding,
  onToggleEnabled,
  onDuplicateBinding,
  onDeleteBinding,
}: Props) {
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);

  useEffect(() => {
    if (!menuOpenId) return;
    function close(e: MouseEvent) {
      if (!(e.target as HTMLElement).closest("[data-binding-menu]")) {
        setMenuOpenId(null);
      }
    }
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [menuOpenId]);

  if (bindings.length === 0) {
    return (
      <p className="py-2 text-center text-[11px] text-white/30">No bindings yet</p>
    );
  }

  return (
    <div className="space-y-1">
      {bindings.map((binding) => (
        <article
          key={binding.id}
          onClick={() => onSelectBinding?.(binding)}
          className={[
            "rounded-md border bg-zinc-900/65 px-2 py-1.5 transition",
            selectedBindingId === binding.id
              ? "border-cyan-300/25 shadow-[inset_0_0_0_1px_rgba(0,180,210,0.12)]"
              : binding.enabled
              ? "border-white/10 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.02)]"
              : "border-white/6 opacity-60",
          ].join(" ")}
        >
          <div className="flex items-center gap-2">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5 leading-none">
                <span className="font-mono text-[10px] text-white/35">Ch {(binding.channel ?? 0) + 1}</span>
                <span className="truncate font-mono text-[11.5px] font-semibold tracking-tight text-white">
                  {binding.triggerLabel}
                </span>
                {binding.triggerCondition && (
                  <span className="font-mono text-[10px] text-white/40">{binding.triggerCondition}</span>
                )}
                <InlineBindingIcon binding={binding} />
              </div>
              <div className="mt-[3px] flex items-center gap-1 leading-none">
                <span className="text-cyan-300/55" aria-hidden>→</span>
                <span className="truncate font-mono text-[10.5px] text-white/55">
                  {binding.actionLabel}
                </span>
              </div>
            </div>
            <div className="relative flex shrink-0 items-center gap-1" data-binding-menu>
              {binding.displayColor && bindingColorHex(binding.displayColor) && (
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: bindingColorHex(binding.displayColor) }}
                  title={binding.displayColor}
                />
              )}
              <KindBadge kind={binding.kind} />
              {(onEditBinding || onToggleEnabled || onDuplicateBinding || onDeleteBinding) && (
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  setMenuOpenId((current) => (current === binding.id ? null : binding.id));
                }}
                className="grid !h-5 !w-5 place-items-center rounded border border-white/8 bg-white/[0.03] !p-0 text-white/45 hover:bg-white/[0.06]"
                aria-label="Binding actions"
                aria-expanded={menuOpenId === binding.id}
              >
                <svg viewBox="0 0 16 16" className="h-3 w-3" fill="currentColor">
                  <circle cx="8" cy="3.5" r="1" />
                  <circle cx="8" cy="8" r="1" />
                  <circle cx="8" cy="12.5" r="1" />
                </svg>
              </button>
              )}
              {menuOpenId === binding.id && (
                <div className="absolute right-0 top-6 z-50 min-w-[128px] rounded border border-white/15 bg-zinc-900 py-0.5 shadow-xl">
                  {onEditBinding && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpenId(null);
                        onEditBinding(binding);
                      }}
                      className="flex w-full items-center gap-2 !px-3 !py-1.5 text-left !text-[11px] text-white/75 hover:bg-white/[0.06]"
                      style={{ background: "transparent", border: "none", borderRadius: 0 }}
                    >
                      <svg viewBox="0 0 16 16" className="h-3 w-3 shrink-0 text-white/40" fill="none" stroke="currentColor" strokeWidth="1.4">
                        <path d="M11 2.5l2.5 2.5-7 7H4v-2.5l7-7z" />
                      </svg>
                      Edit
                    </button>
                  )}
                  {onToggleEnabled && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpenId(null);
                        onToggleEnabled(binding);
                      }}
                      className="flex w-full items-center gap-2 !px-3 !py-1.5 text-left !text-[11px] text-white/75 hover:bg-white/[0.06]"
                      style={{ background: "transparent", border: "none", borderRadius: 0 }}
                    >
                      <span className={[
                        "h-1.5 w-1.5 shrink-0 rounded-full",
                        binding.enabled ? "bg-emerald-300" : "bg-white/30",
                      ].join(" ")} />
                      {binding.enabled ? "Disable" : "Enable"}
                    </button>
                  )}
                  {onDuplicateBinding && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpenId(null);
                        onDuplicateBinding(binding);
                      }}
                      className="flex w-full items-center gap-2 !px-3 !py-1.5 text-left !text-[11px] text-white/75 hover:bg-white/[0.06]"
                      style={{ background: "transparent", border: "none", borderRadius: 0 }}
                    >
                      <svg viewBox="0 0 16 16" className="h-3 w-3 shrink-0 text-white/40" fill="none" stroke="currentColor" strokeWidth="1.4">
                        <rect x="5" y="5" width="8" height="8" rx="1.2" />
                        <path d="M3 11V3h8" />
                      </svg>
                      Duplicate
                    </button>
                  )}
                  {(onEditBinding || onToggleEnabled || onDuplicateBinding) && onDeleteBinding && (
                    <div className="my-0.5 border-t border-white/8" />
                  )}
                  {onDeleteBinding && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpenId(null);
                        onDeleteBinding(binding);
                      }}
                      className="flex w-full items-center gap-2 !px-3 !py-1.5 text-left !text-[11px] text-rose-300/70 hover:bg-white/[0.06]"
                      style={{ background: "transparent", border: "none", borderRadius: 0 }}
                    >
                      <svg viewBox="0 0 16 16" className="h-3 w-3 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.4">
                        <path d="M3 5h10M6 5V3.5h4V5M5.5 5l.5 7.5h4l.5-7.5" />
                      </svg>
                      Delete
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          {!compact && (
            <div className="mt-1.5 flex items-center justify-between gap-2 border-t border-white/[0.04] pt-1 text-[10px] leading-none">
              <span className="truncate">
                <span className="uppercase tracking-[0.14em] text-white/25">Layer </span>
                <span className="text-white/65">{binding.layer}</span>
              </span>
              <div className="flex shrink-0 items-center gap-1">
                <span
                  className={[
                    "inline-flex items-center gap-1 rounded border !px-1.5 !py-[3px] text-[9.5px] uppercase tracking-[0.12em]",
                    binding.enabled
                      ? "border-emerald-300/25 bg-emerald-400/[0.05] text-emerald-100/90"
                      : "border-white/10 bg-white/[0.03] text-white/40",
                  ].join(" ")}
                >
                  <span
                    className={[
                      "h-1 w-1 rounded-full",
                      binding.enabled ? "bg-emerald-300 shadow-[0_0_5px_rgba(52,200,150,0.6)]" : "bg-white/30",
                    ].join(" ")}
                  />
                  {binding.enabled ? "Active" : "Off"}
                </span>
                <span
                  className={[
                    "rounded border !px-1.5 !py-[3px] text-[9.5px] uppercase tracking-[0.12em]",
                    binding.requireArmed
                      ? "border-white/12 bg-white/[0.05] text-white/70"
                      : "border-white/10 bg-white/[0.03] text-white/40",
                  ].join(" ")}
                >
                  {binding.requireArmed ? "Armed" : "Always"}
                </span>
              </div>
            </div>
          )}
        </article>
      ))}
    </div>
  );
}
