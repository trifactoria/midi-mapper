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

// A sharp/accidental note (C#, D#, F#, G#, A#) — semitone with a `#`
// in the standard note-name set. We use this purely as a hierarchy hint
// (recess sharps so the natural row "scans" first), not piano styling.
function isSharp(midi: number) {
  return [1, 3, 6, 8, 10].includes(midi % 12);
}

export function KeyboardGrid({ notes, onNoteClick }: Props) {
  return (
    <section className="rounded-md border border-white/12 bg-white/[0.038] px-3 pb-2 pt-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.055),0_6px_22px_-8px_rgba(0,0,0,0.6)]">
      <div className="mb-1 flex items-center justify-between gap-3">
        <div className="flex items-baseline gap-2">
          <h3 className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/70">
            Note Map
          </h3>
          <span className="text-[10.5px] text-white/40">Click a note to start mapping</span>
        </div>
        <label className="flex !h-6 items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.04] !px-1.5 !text-[10.5px] text-white/75">
          <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.4">
            <path d="M4 7h8M4 9h6M4 11h4" />
          </svg>
          <select
            aria-label="Octave"
            className="!h-5 !rounded !border-white/10 !bg-transparent !px-0.5 !py-0 !text-[10.5px] text-white/85"
            defaultValue="3"
          >
            {[1, 2, 3, 4, 5, 6, 7].map((octave) => (
              <option key={octave} value={octave} className="bg-zinc-900">
                Octave {octave}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* gap-x small, gap-y larger → subtle octave row separation */}
      <div className="grid grid-cols-6 gap-x-1 gap-y-1 sm:grid-cols-8 md:grid-cols-12 md:gap-y-[7px]">
        {notes.map((note) => {
          const sharp = isSharp(note.note);

          // Base surface — naturals sit clearly forward, sharps clearly recede.
          // `!important` + explicit `bg-none` defeats the global `button { background:
          // linear-gradient(...) }` shorthand in globals.css that otherwise overlays a
          // diagonal white sheen on every tile and washes out the contrast.
          const baseSurface = sharp
            ? "!bg-[#070a10] hover:!bg-[#0b1018] bg-none shadow-[inset_0_2px_4px_rgba(0,0,0,0.6)]"
            : "!bg-[#202838] hover:!bg-[#273247] bg-none shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]";

          // Border + name text — naturals always meaningfully brighter than sharps.
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

          // MIDI number color tier — restated explicitly per class.
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
                {note.label.replace(/\d+$/, "")}
              </span>
              <span className={["mt-px font-mono text-[8.5px] leading-none", midiNumberClass].join(" ")}>
                {note.note}
              </span>

              {note.velocity !== undefined && (
                <span className="absolute inset-x-0.5 bottom-0.5 rounded bg-cyan-300/15 !px-0.5 !py-px text-center font-mono text-[8px] leading-none text-cyan-100">
                  v{note.velocity}
                </span>
              )}
            </button>
          );
        })}
      </div>

    </section>
  );
}
