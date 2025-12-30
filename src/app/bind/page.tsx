"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { MidiContextBar } from "../../components/MidiContextBar";
import { NoteGrid } from "../../components/NoteGrid";
import { BindingEditor } from "../../components/BindingEditor";
import { apiGet } from "../../components/useMidiApi";
import type { ContextHeader } from "../../components/types";

export default function BindPage() {
  const [header, setHeader] = useState<ContextHeader | null>(null);
  const [contextId, setContextId] = useState<number | null>(null);

  const [bindings, setBindings] = useState<any[]>([]);
  const [selectedNote, setSelectedNote] = useState<number | null>(null);

  const reloadBindings = useCallback(() => {
    if (!contextId) return;
    apiGet<any[]>(`/api/contexts/${contextId}/bindings`).then(setBindings).catch(console.error);
  }, [contextId]);

  useEffect(() => {
    reloadBindings();
  }, [reloadBindings]);

  const boundMarkers = useMemo(() => {
    const m = new Map<number, string>();
    for (const b of bindings) {
      if (b.trig_type === 1 && typeof b.note === "number" && b.enabled === 1) {
        // Use emoji if provided, otherwise default to "•"
        const marker = b.notify_emoji && b.notify_emoji.trim() ? b.notify_emoji : "•";
        m.set(b.note, marker);
      }
    }
    return m;
  }, [bindings]);

  return (
    <div style={{ padding: 16, display: "grid", gap: 12 }}>
      <h1 style={{ margin: 0 }}>MIDI Mapper</h1>

      <MidiContextBar value={header} onChange={setHeader} onContextId={setContextId} />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 420px", gap: 12, alignItems: "start" }}>
        <NoteGrid
          boundMarkers={boundMarkers}
          selectedNote={selectedNote}
          onSelect={setSelectedNote}
          pressedNote={null}
          armed={true}
        />
        <BindingEditor contextId={contextId} selectedNote={selectedNote} onBindingsChanged={reloadBindings} />
      </div>
    </div>
  );
}

