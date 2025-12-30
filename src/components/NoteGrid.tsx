"use client";

type Props = {
  boundNotes: Set<number>;
  selectedNote: number | null;
  onSelect: (note: number) => void;

  // if false: dim bound indicators (wrong channel/bank/program)
  armed: boolean;

  // Highest note to render (inclusive). MIDI spec is 0..127, but many devices have fewer pads/keys.
  // Set from backend (MAX_NOTE) or env (NEXT_PUBLIC_MIDI_MAX_NOTE) via the page.
  maxNote?: number;
};

function clampInt(v: number, lo: number, hi: number) {
  if (!Number.isFinite(v)) return lo;
  return Math.max(lo, Math.min(hi, Math.trunc(v)));
}

export function NoteGrid({ boundNotes, selectedNote, onSelect, armed, maxNote = 127 }: Props) {
  const hi = clampInt(maxNote, 0, 127);

  // 0..127 => 16 notes per row -> 8 rows (128 cells). We render only up to hi.
  const rows = Math.ceil((hi + 1) / 16);

  return (
    <div style={{ border: "1px solid #333", borderRadius: 8, padding: 10 }}>
      <div style={{ marginBottom: 8, opacity: 0.8 }}>Notes (0–{hi}). Click a note number to bind.</div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(16, minmax(28px, 1fr))",
          gap: 6,
          fontFamily: "monospace",
        }}
      >
        {Array.from({ length: rows * 16 }, (_, k) => {
          const note = k;
          if (note > hi) return <div key={k} />;

          const isSelected = selectedNote === note;
          const isBound = boundNotes.has(note);

          return (
            <button
              key={k}
              onClick={() => onSelect(note)}
              style={{
                border: "1px solid #444",
                borderRadius: 6,
                padding: "6px 0",
                cursor: "pointer",
                opacity: armed ? 1 : 0.35,
                fontWeight: isSelected ? 800 : 400,
              }}
              title={isBound ? "Bound" : "Unbound"}
            >
              {note}
              {isBound ? "*" : ""}
            </button>
          );
        })}
      </div>

      <div style={{ marginTop: 8, opacity: 0.75 }}>* = has a binding in this context (even if match is off).</div>
    </div>
  );
}
