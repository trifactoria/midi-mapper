import { useState } from "react";
import { ICONS } from "../icons";
import type { KeyboardNote, NoteDotColor } from "../v2/types";

type Props = {
  notes: KeyboardNote[];
  onNoteClick?: (note: number) => void;
};

const DOT_COLOR: Record<NoteDotColor, string> = {
  cyan: "bg-cyan-300",
  purple: "bg-purple-300",
  amber: "bg-amber-300",
  orange: "bg-orange-300",
  red: "bg-red-300",
  emerald: "bg-emerald-300",
  violet: "bg-violet-300",
  rose: "bg-rose-300",
  blue: "bg-blue-300",
  slate: "bg-slate-400",
};

function isSharp(midi: number) {
  return [1, 3, 6, 8, 10].includes(midi % 12);
}

const NOTE_RANGES = [
  { id: "oct--1-4", label: "Octaves -1 to 4", start: 0, end: 72 },
  { id: "oct-0-5", label: "Octaves 0 to 5", start: 12, end: 84 },
  { id: "oct-1-6", label: "Octaves 1 to 6", start: 24, end: 96 },
  { id: "oct-2-7", label: "Octaves 2 to 7", start: 36, end: 108 },
] as const;

function NoteIcon({ iconKey, color }: { iconKey: string; color?: string }) {
  const entry = ICONS.find((ic) => ic.key === iconKey);
  if (!entry) return null;
  return (
    <span className="absolute bottom-0.5 left-1/2 -translate-x-1/2" style={{ color: color ?? undefined }}>
      <svg
        viewBox="0 0 24 24"
        className={["h-2.5 w-2.5", color ? "" : "text-white/40"].join(" ")}
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

export function KeyboardGrid({ notes, onNoteClick }: Props) {
  const [rangeId, setRangeId] = useState<(typeof NOTE_RANGES)[number]["id"]>("oct-1-6");
  const range = NOTE_RANGES.find((item) => item.id === rangeId) ?? NOTE_RANGES[2];
  const visibleNotes = notes.filter((n) => n.note >= range.start && n.note < range.end);

  return (
    <section className="rounded-md border border-white/12 bg-white/[0.038] px-3 pb-2 pt-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.055),0_6px_22px_-8px_rgba(0,0,0,0.6)]">
      <div className="mb-1 flex items-center justify-between gap-3">
        <div className="flex items-baseline gap-2">
          <h3 className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/70">
            Note Map
          </h3>
          <span className="text-[10.5px] text-white/40">
            {onNoteClick ? "Click a note to trigger its action" : "Enable Mouse Mode to trigger by click"}
          </span>
        </div>
        <label className="flex !h-6 items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.04] !px-1.5 !text-[10.5px] text-white/75">
          <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.4">
            <path d="M4 7h8M4 9h6M4 11h4" />
          </svg>
          <select
            aria-label="Note range"
            className="!h-5 !min-h-0 !rounded !border-0 !bg-transparent !pl-0.5 !pr-4 !py-0 !text-[10.5px] text-white/85"
            value={rangeId}
            onChange={(e) => setRangeId(e.target.value as (typeof NOTE_RANGES)[number]["id"])}
          >
            {NOTE_RANGES.map((item) => (
              <option key={item.id} value={item.id} className="bg-zinc-900">
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid grid-cols-6 gap-x-1 gap-y-1 sm:grid-cols-8 md:grid-cols-12 md:gap-y-[7px]">
        {visibleNotes.map((note) => {
          const sharp = isSharp(note.note);

          const baseSurface = sharp
            ? "!bg-[#070a10] hover:!bg-[#0b1018] bg-none shadow-[inset_0_2px_4px_rgba(0,0,0,0.6)]"
            : "!bg-[#202838] hover:!bg-[#273247] bg-none shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]";

          let stateClass: string;
          if (note.active) {
            stateClass = sharp
              ? "!border-cyan-300/65 !bg-cyan-300/[0.10] text-white !shadow-[0_0_22px_-4px_rgba(0,180,220,0.35),inset_0_0_0_1px_rgba(0,212,255,0.45)]"
              : "!border-cyan-300/80 !bg-cyan-300/[0.12] text-white !shadow-[0_0_28px_-4px_rgba(0,180,220,0.50),inset_0_0_0_1px_rgba(0,212,255,0.60)]";
          } else if (note.bound) {
            stateClass = sharp
              ? "border-white/[0.10] text-white/[0.58]"
              : "border-white/[0.22] text-white/95";
          } else {
            stateClass = sharp
              ? "border-white/[0.045] text-white/[0.48]"
              : "border-white/[0.16] text-white/90";
          }

          const midiNumberClass = sharp ? "text-white/[0.34]" : "text-white/[0.62]";

          return (
            <button
              type="button"
              key={note.note}
              className={[
                "relative flex aspect-square min-h-[38px] flex-col items-center justify-center rounded border !p-0 text-center transition-colors",
                baseSurface,
                stateClass,
              ].join(" ")}
              title={`${note.note} ${note.label}`}
              onClick={() => onNoteClick?.(note.note)}
            >
              {note.dots && note.dots.length > 0 && (
                <span className="absolute left-0.5 top-0.5 flex gap-0.5">
                  {note.dots.map((color, i) => (
                    <span
                      key={i}
                      className={[
                        "h-1.5 w-1.5 rounded-full",
                        DOT_COLOR[color],
                        sharp ? "shadow-[0_0_2px_currentColor]" : "shadow-[0_0_3px_currentColor]",
                      ].join(" ")}
                    />
                  ))}
                </span>
              )}

              <span className="text-[11px] font-semibold leading-none tracking-tight">
                {note.label.replace(/-?\d+$/, "")}
              </span>
              <span className={["mt-px font-mono text-[8.5px] leading-none", midiNumberClass].join(" ")}>
                {note.note}
              </span>

              {note.velocity !== undefined && (
                <span className="absolute inset-x-0.5 bottom-0.5 rounded bg-cyan-300/15 !px-0.5 !py-px text-center font-mono text-[8px] leading-none text-cyan-100">
                  v{note.velocity}
                </span>
              )}

              {note.icon && !note.velocity && <NoteIcon iconKey={note.icon} color={note.iconColor} />}
            </button>
          );
        })}
      </div>
    </section>
  );
}
