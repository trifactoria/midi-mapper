"use client";

type Props = {
  boundNotes: Set<number>;
  selectedNote: number | null;
  onSelect: (note: number) => void;

  // if false: dim bound indicators (wrong channel/bank/program)
  armed: boolean;

  // which note is currently being pressed (optional highlight)
  liveNote: number | null;
};

function isBlackKey(k: number) {
  // semitone indexes: C=0, C#=1, D=2, D#=3, E=4, F=5, F#=6, G=7, G#=8, A=9, A#=10, B=11
  return k === 1 || k === 3 || k === 6 || k === 8 || k === 10;
}

export function NoteGrid({ boundNotes, selectedNote, onSelect, armed, liveNote }: Props) {
  const octaves = Array.from({ length: 11 }, (_, i) => i); // 0..10 covers 0..127

  return (
    <div style={{ border: "1px solid #333", padding: 12, borderRadius: 12 }}>
      <div style={{ marginBottom: 8, opacity: 0.85, display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>Notes (0–127). Click a note number to bind.</div>
        <div style={{ opacity: 0.8 }}>
          mode match: <b style={{ color: armed ? "lime" : "tomato" }}>{armed ? "YES" : "NO"}</b>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "80px repeat(12, 1fr)", gap: 6, alignItems: "center" }}>
        <div />
        {Array.from({ length: 12 }, (_, i) => (
          <div key={i} style={{ textAlign: "center", opacity: 0.7, fontFamily: "monospace" }}>
            {i}
          </div>
        ))}

        {octaves.map((oct) => (
          <div key={oct} style={{ display: "contents" }}>
            <div style={{ opacity: 0.85 }}>Oct {oct}</div>

            {Array.from({ length: 12 }, (_, k) => {
              const note = oct * 12 + k;
              if (note > 127) return <div key={k} />;

              const black = isBlackKey(k);
              const isBound = boundNotes.has(note);
              const isSelected = selectedNote === note;
              const isLive = liveNote === note;

              const baseBg = black ? "#111" : "#e6e6e6";
              const baseFg = black ? "#f2f2f2" : "#111";

              // bound highlight only when armed (your rule)
              const boundBg = armed ? (black ? "#1e1e1e" : "#d4d4d4") : baseBg;
              const boundBorder = armed ? "#7a7a7a" : "#444";

              const bg =
                isSelected ? "#1f3a5a" : isLive ? "#2c6b2c" : isBound ? boundBg : baseBg;

              const fg = isSelected ? "#fff" : isLive ? "#fff" : baseFg;

              return (
                <button
                  key={k}
                  onClick={() => onSelect(note)}
                  style={{
                    padding: "10px 0",
                    border: `1px solid ${isBound ? boundBorder : "#444"}`,
                    borderRadius: 10,
                    cursor: "pointer",
                    background: bg,
                    color: fg,
                    fontFamily: "monospace",
                    fontWeight: isBound && armed ? 700 : 500,
                    opacity: armed ? 1 : 0.88,
                  }}
                  title={`note=${note} (oct=${oct}, key=${k})`}
                >
                  {note}
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
