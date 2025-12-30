"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { apiGet, apiPost, apiSendContext } from "./useMidiApi";
import type { ContextHeader, Port } from "./types";

type Props = {
  value: ContextHeader | null;
  onChange: (v: ContextHeader) => void;
  onContextId: (contextId: number) => void;
};

function clampInt(v: number, lo: number, hi: number) {
  if (!Number.isFinite(v)) return lo;
  return Math.max(lo, Math.min(hi, Math.trunc(v)));
}

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

function range(n: number) {
  return Array.from({ length: n }, (_, i) => i);
}

export function MidiContextBar({ value, onChange, onContextId }: Props) {
  const [ports, setPorts] = useState<Port[]>([]);
  const [err, setErr] = useState<string>("");

  // Local draft (controlled-ish)
  const [draft, setDraft] = useState<ContextHeader | null>(value);

  // Status UI
  const [saveStatus, setSaveStatus] = useState<string>("");
  const [sendStatus, setSendStatus] = useState<string>("");

  const debounceRef = useRef<number | null>(null);
  const lastContextKeyRef = useRef<string>("");

  // Options (these match your device constraints / typical MIDI)
  const dawOptions = useMemo(() => range(12), []); // 0..11
  const presetOptions = useMemo(() => range(16), []); // 0..15
  const channelOptions = useMemo(() => range(16), []); // 0..15
  const midi7bitOptions = useMemo(() => range(128), []); // 0..127

  // Load ports
  useEffect(() => {
    let alive = true;
    apiGet<Port[]>("/api/ports")
      .then((p) => {
        if (!alive) return;
        setPorts(p);
        setErr("");
      })
      .catch((e) => alive && setErr(String(e)));
    return () => {
      alive = false;
    };
  }, []);

  // Initialize header from defaults or fallback
  useEffect(() => {
    if (!ports.length) return;
    if (draft) return;

    let alive = true;

    // Try to load defaults first
    apiGet<ContextHeader>("/api/defaults")
      .then((defaults) => {
        if (!alive) return;

        // Verify port_id exists in current ports
        const portExists = ports.some((p) => p.id === defaults.port_id);
        const init: ContextHeader = portExists
          ? defaults
          : {
              ...defaults,
              port_id: ports[0].id, // Fallback to first port if saved port doesn't exist
            };

        setDraft(init);
        onChange(init);
      })
      .catch(() => {
        // Fallback if defaults endpoint fails
        if (!alive) return;
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
      });

    return () => {
      alive = false;
    };
  }, [ports, draft, onChange]);

  // Sync down from parent (rare, but safe)
  useEffect(() => {
    if (!value) return;
    if (!draft || !sameHeader(value, draft)) setDraft(value);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const updateDraft = (patch: Partial<ContextHeader>) => {
    if (!draft) return;
    const next: ContextHeader = { ...draft, ...patch };
    setDraft(next);
    onChange(next);
  };

  const contextKey = (h: ContextHeader) =>
    `${h.daw_slot}|${h.preset_slot}|${h.port_id}|${h.channel}|${h.bank_msb}|${h.bank_lsb}|${h.program}`;

  // Push active selection + debounce context lookup
  useEffect(() => {
    if (!draft) return;

    setSaveStatus("Syncing…");
    setErr("");

    // 1) Always push active_selection (match gating)
    apiPost("/api/active_selection/set", draft).catch((e) => setErr(String(e)));

    // 2) Debounced get_or_create => context_id
    if (debounceRef.current) window.clearTimeout(debounceRef.current);

    debounceRef.current = window.setTimeout(() => {
      const key = contextKey(draft);

      // Avoid spamming if nothing actually changed
      if (lastContextKeyRef.current === key) {
        setSaveStatus("");
        return;
      }
      lastContextKeyRef.current = key;

      apiPost<{ context_id: number }>("/api/contexts/get_or_create", draft)
        .then((r) => {
          onContextId(r.context_id);
          setSaveStatus(`Context: ${r.context_id}`);
        })
        .catch((e) => {
          setErr(String(e));
          setSaveStatus("");
        });
    }, 150);

    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [draft, onContextId]);

  async function onSaveAsDefaults() {
    if (!draft) return;

    setErr("");
    setSendStatus("Saving…");

    try {
      await apiPost("/api/defaults/save", draft);
      setSendStatus("Saved as defaults");
      setTimeout(() => setSendStatus(""), 2000);
    } catch (e: any) {
      setSendStatus(e?.message ?? "Save failed");
    }
  }

  if (!draft) return <div style={{ padding: 12 }}>Loading ports…</div>;

  const disabled = !ports.length;

  return (
    <div style={{ display: "grid", gap: 10 }}>
      {err ? (
        <div style={{ padding: 10, border: "1px solid tomato", color: "tomato", borderRadius: 8 }}>
          {err}
        </div>
      ) : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(7, minmax(120px, 1fr))",
          gap: 8,
          alignItems: "end",
        }}
      >
        <label style={{ display: "grid", gap: 4 }}>
          DAW
          <select
            value={draft.daw_slot}
            disabled={disabled}
            onChange={(e) => updateDraft({ daw_slot: clampInt(Number(e.target.value), 0, 11) })}
            style={{ width: "100%" }}
          >
            {dawOptions.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: "grid", gap: 4 }}>
          Preset
          <select
            value={draft.preset_slot}
            disabled={disabled}
            onChange={(e) => updateDraft({ preset_slot: clampInt(Number(e.target.value), 0, 15) })}
            style={{ width: "100%" }}
          >
            {presetOptions.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: "grid", gap: 4 }}>
          Port
          <select
            value={draft.port_id}
            disabled={disabled}
            onChange={(e) => updateDraft({ port_id: Number(e.target.value) })}
            style={{ width: "100%" }}
          >
            {ports.map((p) => (
              <option key={p.id} value={p.id}>
                {p.id}: {p.name}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: "grid", gap: 4 }}>
          Ch
          <select
            value={draft.channel}
            disabled={disabled}
            onChange={(e) => updateDraft({ channel: clampInt(Number(e.target.value), 0, 15) })}
            style={{ width: "100%" }}
          >
            {channelOptions.map((n) => (
              <option key={n} value={n}>
                {n + 1} (ch {n})
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: "grid", gap: 4 }}>
          MSB
          <select
            value={draft.bank_msb}
            disabled={disabled}
            onChange={(e) => updateDraft({ bank_msb: clampInt(Number(e.target.value), 0, 127) })}
            style={{ width: "100%" }}
          >
            {midi7bitOptions.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: "grid", gap: 4 }}>
          LSB
          <select
            value={draft.bank_lsb}
            disabled={disabled}
            onChange={(e) => updateDraft({ bank_lsb: clampInt(Number(e.target.value), 0, 127) })}
            style={{ width: "100%" }}
          >
            {midi7bitOptions.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: "grid", gap: 4 }}>
          Program
          <select
            value={draft.program}
            disabled={disabled}
            onChange={(e) => updateDraft({ program: clampInt(Number(e.target.value), 0, 127) })}
            style={{ width: "100%" }}
          >
            {midi7bitOptions.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <button
          onClick={onSaveAsDefaults}
          disabled={disabled}
          title="Save current header values as startup defaults"
          className="btn"
        >
          Save As Defaults
        </button>

        {sendStatus ? <span style={{ opacity: 0.85 }}>{sendStatus}</span> : null}
      </div>
    </div>
  );
}
