"use client";

import { useEffect, useRef, useState } from "react";

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
  derived: { bank_msb: number; bank_lsb: number; program: number };
};

export default function MidiConsole() {
  const [events, setEvents] = useState<MidiEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8765/ws/events");
    wsRef.current = ws;
    let pingTimer: ReturnType<typeof setInterval> | null = null;

    ws.onopen = () => {
      // send keepalive pings so FastAPI handler stays alive
      pingTimer = setInterval(() => ws.send("ping"), 1000);
    };

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data) as MidiEvent;
      setEvents((prev) => [msg, ...prev].slice(0, 200));
    };

    ws.onclose = () => {
      if (pingTimer) clearInterval(pingTimer);
    };

    return () => {
      if (pingTimer) clearInterval(pingTimer);
      try {
        ws.close();
      } catch {}
    };
  }, []);

  return (
    <div style={{ padding: 16, fontFamily: "monospace" }}>
      <h2>MIDI Event Console</h2>
      <div style={{ whiteSpace: "pre-wrap", border: "1px solid #444", padding: 12, height: "75vh", overflow: "auto" }}>
        {events.map((e, idx) => (
          <div key={idx}>
            [{new Date(e.ts * 1000).toLocaleTimeString()}] {e.port_name} → {e.type} ch={e.channel ?? "-"}{" "}
            {e.type === "note_on" || e.type === "note_off"
              ? `note=${e.note} vel=${e.velocity}`
              : e.type === "control_change"
              ? `cc=${e.cc} value=${e.value}`
              : e.type === "pitchwheel"
              ? `pitch=${e.pitch}`
              : e.type === "program_change"
              ? `program=${e.program}`
              : ""}
            {"  "}derived(msb={e.derived.bank_msb} lsb={e.derived.bank_lsb} prog={e.derived.program})
          </div>
        ))}
      </div>
    </div>
  );
}
