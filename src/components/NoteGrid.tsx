"use client";

import React from "react";

type Props = {
  boundMarkers: Map<number, string>; // note -> emoji/marker (default "•")
  selectedNote: number | null;
  onSelect: (note: number) => void;

  /** Most recently observed note from MIDI stream (note_on) */
  pressedNote: number | null;

  /** If false, dim the whole grid (e.g. selection mismatch) */
  armed: boolean;

  /** Optional limit for how many notes to render */
  maxNote?: number; // default 127
};

const NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

function clampInt(v: number, lo: number, hi: number) {
  if (!Number.isFinite(v)) return lo;
  return Math.max(lo, Math.min(hi, Math.trunc(v)));
}

function pc(note: number) {
  return ((note % 12) + 12) % 12;
}

function isBlackKey(note: number) {
  const p = pc(note);
  return p === 1 || p === 3 || p === 6 || p === 8 || p === 10;
}

function noteName(note: number) {
  const p = pc(note);
  const oct = Math.floor(note / 12) - 1; // MIDI: 60 = C4
  return `${NAMES[p]}${oct}`;
}

export function NoteGrid({
  boundMarkers,
  selectedNote,
  onSelect,
  pressedNote,
  armed,
  maxNote = 127,
}: Props) {
  const hi = clampInt(maxNote, 0, 127);
  const cols = 12;
  const rows = Math.ceil((hi + 1) / cols);

  // Styling tokens (easy to tweak)
  const whiteBg = "#f9f9f9";
  const whiteFg = "#0a0a0a";
  const blackBg = "#1a1a1a";
  const blackFg = "#f0f0f0";

  const pressedOutline = "3px solid #00d4ff";
  const pressedGlow = "0 0 0 6px rgba(0,212,255,0.25), 0 0 28px rgba(0,212,255,0.45)";
  const selectedOutline = "2px solid #00bd7d";
  const selectedGlow = "0 0 0 5px rgba(0,189,125,0.22), 0 0 18px rgba(0,189,125,0.35)";

  const baseCell: React.CSSProperties = {
    borderRadius: 10,
    border: "1px solid rgba(255,255,255,0.08)",
    padding: "10px 6px",
    cursor: "pointer",
    userSelect: "none",
    display: "grid",
    gap: 2,
    alignContent: "center",
    justifyItems: "center",
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    transition: "transform 70ms ease, box-shadow 70ms ease, outline 70ms ease, filter 70ms ease",
  };

  return (
    <div style={{ border: "1px solid #2a2a2a", borderRadius: 12, padding: 12 }}>
      <div style={{ marginBottom: 10, display: "flex", gap: 12, alignItems: "baseline" }}>
        <div style={{ opacity: 0.9 }}>Notes (0–{hi})</div>
        <div style={{ opacity: 0.65, fontSize: 12 }}>
          pressed:{" "}
          {pressedNote == null ? "—" : `${pressedNote} (${noteName(pressedNote)})`}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${cols}, minmax(56px, 1fr))`,
          gap: 10,
          opacity: armed ? 1 : 0.35,
        }}
      >
        {Array.from({ length: rows * cols }, (_, idx) => {
          const note = idx;
          if (note > hi) return <div key={idx} />;

          const black = isBlackKey(note);
          const marker = boundMarkers.get(note);
          const isBound = marker !== undefined;
          const isSelected = selectedNote === note;
          const isPressed = pressedNote === note;

          // Make pressed always win over selected, and both win over bound
          const outline = isPressed
            ? pressedOutline
            : isSelected
            ? selectedOutline
            : "none";

          const boxShadow = isPressed
            ? pressedGlow
            : isSelected
            ? selectedGlow
            : isBound
            ? "0 0 0 2px rgba(255,255,255,0.08)"
            : undefined;

          const transform = isPressed ? "translateY(-2px) scale(1.03)" : isSelected ? "translateY(-1px)" : undefined;

          const bg = black ? blackBg : whiteBg;
          const fg = black ? blackFg : whiteFg;

          return (
            <button
              key={idx}
              onClick={() => onSelect(note)}
              style={{
                ...baseCell,
                background: bg,
                color: fg,
                outline,
                boxShadow,
                transform,
                filter: isPressed ? "brightness(1.10)" : undefined,
              }}
              title={`${note} • ${noteName(note)}${isBound ? " • bound" : ""}`}
            >
              <div style={{ fontSize: 14, fontWeight: 900 }}>{note}</div>
              <div style={{ fontSize: 12, opacity: 0.78 }}>{noteName(note)}</div>

              {/* Bound indicator: emoji or default marker */}
              <div style={{ height: 14, fontSize: 14, opacity: 1, fontWeight: 600 }}>
                {isBound ? marker : " "}
              </div>
            </button>
          );
        })}
      </div>

      <div style={{ marginTop: 10, opacity: 0.7, fontSize: 12 }}>
        emoji/marker = bound • cyan glow = pressed • green glow = selected
      </div>
    </div>
  );
}
