"use client";

import { useEffect, useRef, useState } from "react";
import { apiGet, apiPost } from "./useMidiApi";
import type { ContextHeader, Port } from "./types";

function clampInt(v: number, lo: number, hi: number) {
  if (!Number.isFinite(v)) return lo;
  return Math.max(lo, Math.min(hi, Math.trunc(v)));
}

type Props = {
  value: ContextHeader | null;
  onChange: (v: ContextHeader) => void;
  onContextId: (contextId: number) => void;
};

function sameHeader(a: ContextHeader, b: ContextHeader) {
  return (
    a.daw_slot === b.daw_slot &&
    a.preset_slot === b.preset_slot &&
    a.port_id === b.port_id &&
    a.channel === b.channel &&
    a.bank_msb === b.bank_msb &&
    a.bank_lsb === b.bank_lsb &&
    a.program === b.program
  );
}

export function MidiContextBar({ value, onChange, onContextId }: Props) {
  const [ports, setPorts] = useState<Port[]>([]);
  const [err, setErr] = useState<string>("");

  const [draft, setDraft] = useState<ContextHeader | null>(value);
  const debounceRef = useRef<number | null>(null);

  useEffect(() => {
    apiGet<Port[]>("/api/ports")
      .then(setPorts)
      .catch((e) => setErr(String(e)));
  }, []);

  // init default if none
  useEffect(() => {
    if (!ports.length) return;
    if (draft) return;

    const init: ContextHeader = {
      daw_slot: 0,
      preset_slot: 0,
      port_id: ports[0].id,
      channel: 0,
      bank_msb: 0,
      bank_lsb: 0,
      program: 0,
    };

    setDraft(init);
    onChange(init);
  }, [ports, draft, onChange]);

  // sync from parent if parent changes it (rare, but safe)
  useEffect(() => {
    if (!value) return;
    if (!draft || !sameHeader(value, draft)) {
      setDraft(value);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  // whenever draft changes:
  // 1) push active_selection to backend (match gating)
  // 2) debounced get_or_create context_id
  useEffect(() => {
    if (!draft) return;

    apiPost("/api/active_selection/set", draft).catch((e) => setErr(String(e)));

    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      apiPost<{ context_id: number }>("/api/contexts/get_or_create", draft)
        .then((r) => onContextId(r.context_id))
        .catch((e) => setErr(String(e)));
    }, 120);

    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [draft, onContextId]);

  if (!draft) return <div style={{ padding: 12 }}>Loading ports…</div>;

  const setField = (k: keyof ContextHeader, n: number) => {
    const next: ContextHeader = { ...draft, [k]: n };
    setDraft(next);
    onChange(next);
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(120px, 1fr))", gap: 8 }}>
      {err ? <div style={{ gridColumn: "1 / -1", color: "tomato" }}>{err}</div> : null}

      <label>
        DAW
        <input
          type="number"
          value={draft.daw_slot}
          min={0}
          max={11}
          onChange={(e) => setField("daw_slot", clampInt(Number(e.target.value), 0, 11))}
          style={{ width: "100%" }}
        />
      </label>

      <label>
        Preset
        <input
          type="number"
          value={draft.preset_slot}
          min={0}
          max={15}
          onChange={(e) => setField("preset_slot", clampInt(Number(e.target.value), 0, 15))}
          style={{ width: "100%" }}
        />
      </label>

      <label>
        Port
        <select
          value={draft.port_id}
          onChange={(e) => setField("port_id", Number(e.target.value))}
          style={{ width: "100%" }}
        >
          {ports.map((p) => (
            <option key={p.id} value={p.id}>
              {p.id}: {p.name}
            </option>
          ))}
        </select>
      </label>

      <label>
        Ch
        <input
          type="number"
          value={draft.channel}
          min={0}
          max={15}
          onChange={(e) => setField("channel", clampInt(Number(e.target.value), 0, 15))}
          style={{ width: "100%" }}
        />
      </label>

      <label>
        MSB
        <input
          type="number"
          value={draft.bank_msb}
          min={0}
          max={127}
          onChange={(e) => setField("bank_msb", clampInt(Number(e.target.value), 0, 127))}
          style={{ width: "100%" }}
        />
      </label>

      <label>
        LSB
        <input
          type="number"
          value={draft.bank_lsb}
          min={0}
          max={127}
          onChange={(e) => setField("bank_lsb", clampInt(Number(e.target.value), 0, 127))}
          style={{ width: "100%" }}
        />
      </label>

      <label>
        Program
        <input
          type="number"
          value={draft.program}
          min={0}
          max={127}
          onChange={(e) => setField("program", clampInt(Number(e.target.value), 0, 127))}
          style={{ width: "100%" }}
        />
      </label>
    </div>
  );
}
