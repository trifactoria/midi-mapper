"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MidiContextBar } from "../components/MidiContextBar";
import { NoteGrid } from "../components/NoteGrid";
import { BindingEditor } from "../components/BindingEditor";
import { apiGet, API_BASE } from "../components/useMidiApi";
import type { ContextHeader } from "../components/types";

type Derived = { bank_msb: number; bank_lsb: number; program: number };
type MidiEventRaw = any;

function normalizeDerived(msg: MidiEventRaw): {
  derived: Derived;
  derived_ch?: Derived;
  derived_port?: Derived;
} {
  // Preferred flat schema
  if (msg?.derived && typeof msg.derived.bank_msb === "number") {
    return {
      derived: msg.derived,
      derived_ch: msg.derived_ch,
      derived_port: msg.derived_port,
    };
  }
  // Older nested schema fallback
  if (msg?.derived?.derived_port && typeof msg.derived.derived_port.bank_msb === "number") {
    return {
      derived: msg.derived.derived_port,
      derived_ch: msg.derived.derived_ch,
      derived_port: msg.derived.derived_port,
    };
  }
  return { derived: { bank_msb: 0, bank_lsb: 0, program: 0 } };
}

type MidiEvent = {
  ts: number;
  port_name: string;
  type: string;
  channel: number | null;
  note: number | null;
  velocity: number | null;
  cc: number | null;
  value: number | null;
  pitch: number | null;
  program: number | null;

  derived: Derived;
  derived_ch?: Derived;
  derived_port?: Derived;

  context_match?: boolean;
  observed_note_channel?: number | null;

  active_context_id?: number | null;
  binding_match?: any | null;
  keygrab_enabled?: boolean;
};

export default function Home() {
  const [header, setHeader] = useState<ContextHeader | null>(null);
  const [contextId, setContextId] = useState<number | null>(null);
  const [bindings, setBindings] = useState<any[]>([]);
  const [selectedNote, setSelectedNote] = useState<number | null>(null);

  const [keygrab, setKeygrab] = useState<boolean>(true);
  const [events, setEvents] = useState<MidiEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  // FOLLOW MODE: when true, header (Ch/MSB/LSB/Program) auto-tracks observed MIDI
  const [followObserved, setFollowObserved] = useState<boolean>(true);
  const userEditingRef = useRef<boolean>(false);
  const editTimeoutRef = useRef<number | null>(null);

  // Observed live state (what the keyboard is emitting)
  const [observed, setObserved] = useState<{
    port_name: string | null;
    channel: number | null;
    note_channel: number | null;
    derived: Derived;
    ts: number | null;
  }>({
    port_name: null,
    channel: null,
    note_channel: null,
    derived: { bank_msb: 0, bank_lsb: 0, program: 0 },
    ts: null,
  });

  const reloadBindings = useCallback(() => {
    if (!contextId) return;
    apiGet<any[]>(`/api/contexts/${contextId}/bindings`).then(setBindings).catch(console.error);
  }, [contextId]);

  // When context changes: reload bindings + set active context in backend (for WS binding_match)
  useEffect(() => {
    if (!contextId) return;
    reloadBindings();
    fetch(`${API_BASE}/api/active_context/set?context_id=${contextId}`, { method: "POST" }).catch(console.error);
  }, [contextId, reloadBindings]);

  // Load keygrab state on mount
  useEffect(() => {
    apiGet<{ enabled: boolean }>("/api/keygrab")
      .then((r) => setKeygrab(r.enabled))
      .catch(console.error);
  }, []);

  // Helper: mark user editing so we don't fight them
  const markUserEditing = useCallback(() => {
    userEditingRef.current = true;
    if (editTimeoutRef.current) window.clearTimeout(editTimeoutRef.current);
    editTimeoutRef.current = window.setTimeout(() => {
      userEditingRef.current = false;
    }, 1200);
  }, []);

  // WebSocket console
  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8765/ws/events");
    wsRef.current = ws;

    ws.onopen = () => {
      const t = setInterval(() => ws.send("ping"), 1000);
      (ws as any).__t = t;
    };

    ws.onmessage = (ev) => {
      const raw = JSON.parse(ev.data) as MidiEventRaw;
      const pack = normalizeDerived(raw);

      const msg: MidiEvent = {
        ts: raw.ts,
        port_name: raw.port_name,
        type: raw.type,
        channel: raw.channel ?? null,
        note: raw.note ?? null,
        velocity: raw.velocity ?? null,
        cc: raw.cc ?? null,
        value: raw.value ?? null,
        pitch: raw.pitch ?? null,
        program: raw.program ?? null,

        derived: pack.derived,
        derived_ch: pack.derived_ch,
        derived_port: pack.derived_port,

        context_match: raw.context_match,
        observed_note_channel: raw.observed_note_channel ?? null,

        active_context_id: raw.active_context_id ?? null,
        binding_match: raw.binding_match ?? null,
        keygrab_enabled: raw.keygrab_enabled ?? undefined,
      };

      setEvents((prev) => [msg, ...prev].slice(0, 250));

      const noteCh = msg.observed_note_channel ?? null;
      setObserved({
        port_name: msg.port_name ?? null,
        channel: msg.channel ?? null,
        note_channel: noteCh,
        derived: msg.derived, // port-level sticky (best for your Oxygen behavior)
        ts: msg.ts,
      });

      // ✅ This is the key behavior you want:
      // Auto-update the HEADER selection from observed MIDI, as long as followObserved is ON
      // and the user is not actively editing inputs.
      if (followObserved && !userEditingRef.current) {
        setHeader((prev) => {
          if (!prev) return prev;

          // channel should follow note channel when available, else event channel
          const ch = (noteCh ?? msg.channel ?? prev.channel) as number;

          // MSB/LSB/Program follow sticky derived (port-level)
          const next: ContextHeader = {
            ...prev,
            channel: ch,
            bank_msb: msg.derived.bank_msb,
            bank_lsb: msg.derived.bank_lsb,
            program: msg.derived.program,
          };
          return next;
        });
      }

      // auto-select note when you press a note
      if (msg.type === "note_on" && msg.note != null && msg.velocity && msg.velocity > 0) {
        setSelectedNote(msg.note);
      }
    };

    ws.onclose = () => {
      const t = (ws as any).__t;
      if (t) clearInterval(t);
    };

    return () => {
      try {
        ws.close();
      } catch {}
    };
  }, [followObserved]);

  const boundNotes = useMemo(() => {
    const s = new Set<number>();
    for (const b of bindings) {
      if (b.trig_type === 1 && typeof b.note === "number" && b.enabled === 1) s.add(b.note);
    }
    return s;
  }, [bindings]);

  const liveNote = useMemo(() => {
    const e = events[0];
    if (!e) return null;
    if (e.type === "note_on" && e.note != null && (e.velocity ?? 0) > 0) return e.note;
    return null;
  }, [events]);

  // "armed" = header matches what’s being emitted right now (local check)
  const armed = useMemo(() => {
    if (!header) return false;
    const ch = observed.note_channel ?? observed.channel ?? null;
    if (ch == null) return false;
    if (ch !== header.channel) return false;
    if (observed.derived.bank_msb !== header.bank_msb) return false;
    if (observed.derived.bank_lsb !== header.bank_lsb) return false;
    if (observed.derived.program !== header.program) return false;
    return true;
  }, [header, observed]);

  async function toggleKeygrab() {
    const next = !keygrab;
    setKeygrab(next);
    await fetch(`${API_BASE}/api/keygrab/set?enabled=${next ? "true" : "false"}`, { method: "POST" });
  }

  function snapHeaderToObserved() {
    if (!header) return;
    const ch = observed.note_channel ?? observed.channel ?? header.channel ?? 0;
    setHeader({
      ...header,
      channel: ch as number,
      bank_msb: observed.derived.bank_msb,
      bank_lsb: observed.derived.bank_lsb,
      program: observed.derived.program,
    });
  }

  return (
    <div style={{ padding: 16, display: "grid", gap: 12 }}>
      <h1 style={{ margin: 0 }}>MIDI Mapper (Setup Mode)</h1>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <div style={{ opacity: 0.8 }}>
          Local keygrab running: <b>{keygrab ? "YES" : "NO"}</b>
        </div>
        <button onClick={toggleKeygrab}>{keygrab ? "Stop keygrab" : "Start keygrab"}</button>
      </div>

      {/* Observed (live) state */}
      <div style={{ border: "1px solid #333", borderRadius: 12, padding: 12, opacity: 0.95 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
          <div>
            <b>Observed</b>{" "}
            <span style={{ opacity: 0.8 }}>
              (last event {observed.ts ? new Date(observed.ts * 1000).toLocaleTimeString() : "—"})
            </span>
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <label style={{ display: "flex", gap: 6, alignItems: "center", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={followObserved}
                onChange={(e) => setFollowObserved(e.target.checked)}
              />
              Follow observed
            </label>

            <button onClick={snapHeaderToObserved}>Snap header → observed</button>

            <div>
              match: <b style={{ color: armed ? "lime" : "tomato" }}>{armed ? "YES" : "NO"}</b>
            </div>
          </div>
        </div>

        <div style={{ fontFamily: "monospace", marginTop: 8, whiteSpace: "pre-wrap" }}>
          {`port=${observed.port_name ?? "—"}  `}
          {`event_ch=${observed.channel ?? "—"}  `}
          {`note_ch=${observed.note_channel ?? "—"}\n`}
          {`bank(msb=${observed.derived.bank_msb} lsb=${observed.derived.bank_lsb}) prog=${observed.derived.program}`}
        </div>
      </div>

      {/* IMPORTANT: markUserEditing is called from here */}
      <MidiContextBar
        value={header}
        onChange={(v) => {
          markUserEditing();
          setHeader(v);
        }}
        onContextId={setContextId}
      />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 420px", gap: 12, alignItems: "start" }}>
        <NoteGrid
          boundNotes={boundNotes}
          selectedNote={selectedNote}
          onSelect={setSelectedNote}
          armed={armed}
          liveNote={liveNote}
        />
        <BindingEditor contextId={contextId} selectedNote={selectedNote} onBindingsChanged={reloadBindings} />
      </div>

      <div style={{ border: "1px solid #333", borderRadius: 12, padding: 12 }}>
        <div style={{ marginBottom: 8, display: "flex", justifyContent: "space-between", gap: 12 }}>
          <div>
            <b>Live MIDI Console</b> (binding_match shows only when header selection matches and keygrab is enabled)
          </div>
          <div style={{ opacity: 0.8 }}>active_context_id: {contextId ?? "—"}</div>
        </div>

        <div
          style={{
            whiteSpace: "pre-wrap",
            fontFamily: "monospace",
            border: "1px solid #444",
            padding: 12,
            height: "40vh",
            overflow: "auto",
          }}
        >
          {events.map((e, idx) => {
            const dch = e.derived_ch ?? e.derived;
            const dpt = e.derived_port ?? e.derived;

            const base =
              `[${new Date(e.ts * 1000).toLocaleTimeString()}] ` +
              `${e.port_name} → ${e.type} ` +
              `ch=${e.channel ?? "-"} ` +
              (e.type === "note_on" || e.type === "note_off"
                ? `note=${e.note} vel=${e.velocity}`
                : e.type === "control_change"
                ? `cc=${e.cc} value=${e.value}`
                : e.type === "pitchwheel"
                ? `pitch=${e.pitch}`
                : e.type === "program_change"
                ? `program=${e.program}`
                : "") +
              `  derived_ch(msb=${dch.bank_msb} lsb=${dch.bank_lsb} prog=${dch.program})` +
              `  derived_port(msb=${dpt.bank_msb} lsb=${dpt.bank_lsb} prog=${dpt.program})` +
              `  match=${e.context_match ? "Y" : "N"}`;

            const match = e.binding_match
              ? `\n    BINDING: trig_type=${e.binding_match.trig_type} note=${e.binding_match.note} cc=${e.binding_match.cc}\n    CMD: ${e.binding_match.command}`
              : "";

            return (
              <div key={idx}>
                {base}
                {match}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
