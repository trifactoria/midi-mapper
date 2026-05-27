"use client";

import { useEffect, useRef, useState } from "react";
import { ICONS } from "./icons";

type Props = {
  value: string;
  onChange: (key: string) => void;
};

function IconSvg({ paths, fill }: { paths: string[]; fill?: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-4 w-4"
      fill={fill ? "currentColor" : "none"}
      stroke={fill ? "none" : "currentColor"}
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths.map((d, i) => (
        <path key={i} d={d} />
      ))}
    </svg>
  );
}

export function IconPicker({ value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = ICONS.find((ic) => ic.key === value);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={[
          "flex items-center gap-1 rounded border !px-1.5 !py-[3px] transition",
          open
            ? "border-cyan-300/30 bg-cyan-300/[0.08] text-cyan-100"
            : "border-white/10 bg-white/[0.04] text-white/55 hover:bg-white/[0.07]",
        ].join(" ")}
        aria-label="Icon picker"
        title={selected?.label ?? "No icon"}
      >
        {selected ? (
          <IconSvg paths={selected.paths} fill={selected.fill} />
        ) : (
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M9 12h6M12 9v6" />
          </svg>
        )}
        <svg viewBox="0 0 10 6" className="h-1.5 w-1.5" fill="currentColor">
          <path d="M0 0l5 6 5-6H0z" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full z-30 mt-1 w-56 rounded-md border border-white/12 bg-zinc-900 p-2 shadow-xl">
          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-[9.5px] uppercase tracking-[0.14em] text-white/40">Icon</span>
            {value && (
              <button
                type="button"
                onClick={() => { onChange(""); setOpen(false); }}
                className="text-[9.5px] text-white/35 hover:text-white/60"
              >
                Clear
              </button>
            )}
          </div>
          <div className="grid grid-cols-7 gap-0.5">
            {ICONS.map((ic) => (
              <button
                key={ic.key}
                type="button"
                title={ic.label}
                onClick={() => { onChange(ic.key); setOpen(false); }}
                className={[
                  "grid h-7 w-7 place-items-center rounded transition",
                  value === ic.key
                    ? "bg-cyan-300/15 text-cyan-200 ring-1 ring-cyan-300/30"
                    : "text-white/45 hover:bg-white/[0.06] hover:text-white/80",
                ].join(" ")}
              >
                <IconSvg paths={ic.paths} fill={ic.fill} />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
