"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { apiGet, apiPost } from "./useMidiApi";
import type { ContextHeader, Port } from "./types";
import { Modal } from "./Modal";

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

type ContextWithBindings = {
  id: number;
  daw_slot: number;
  preset_slot: number;
  port_id: number;
  channel: number;
  bank_msb: number;
  bank_lsb: number;
  program: number;
  binding_count: number;
  label: string | null;
  display_label: string;
};

type ContextExport = {
  version?: number;
  context?: unknown;
  bindings?: unknown[];
  [key: string]: unknown;
};

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function MidiContextBar({ value, onChange, onContextId }: Props) {
  const [ports, setPorts] = useState<Port[]>([]);
  const [err, setErr] = useState<string>("");
  const [contextsLoadError, setContextsLoadError] = useState<string>("");
  const [contextsWithBindings, setContextsWithBindings] = useState<ContextWithBindings[]>([]);

  // Local draft (controlled-ish)
  const [draft, setDraft] = useState<ContextHeader | null>(value);

  // Status UI
  const [sendStatus, setSendStatus] = useState<string>("");

  // Context label editing
  const [currentContextId, setCurrentContextId] = useState<number | null>(null);
  const [contextLabel, setContextLabel] = useState<string>("");
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [modalLabelInput, setModalLabelInput] = useState("");

  // Import/Export modal
  const [showImportExportModal, setShowImportExportModal] = useState(false);
  const [exportJson, setExportJson] = useState<string>("");
  const [importJson, setImportJson] = useState<string>("");
  const [importMode, setImportMode] = useState<"merge" | "replace">("merge");
  const [importExportStatus, setImportExportStatus] = useState<string>("");

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

  // Refresh contexts list (can be called manually or on events)
  const refreshContexts = async () => {
    try {
      const contexts = await apiGet<ContextWithBindings[]>("/api/contexts/with_bindings");
      setContextsWithBindings(contexts);
      setContextsLoadError(""); // Clear any previous error
    } catch (e: unknown) {
      const errorMsg = errorMessage(e, String(e));
      setContextsLoadError(`Failed to load contexts: ${errorMsg}`);
      console.error("Failed to load contexts:", e);
    }
  };

  // Load ALL contexts with bindings once (for cascading hints)
  useEffect(() => {
    refreshContexts();
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

    setErr("");

    // 1) Always push active_selection (match gating)
    apiPost("/api/active_selection/set", draft).catch((e) => setErr(String(e)));

    // 2) Debounced get_or_create => context_id
    if (debounceRef.current) window.clearTimeout(debounceRef.current);

    debounceRef.current = window.setTimeout(() => {
      const key = contextKey(draft);

      // Avoid spamming if nothing actually changed
      if (lastContextKeyRef.current === key) {
        return;
      }
      lastContextKeyRef.current = key;

      apiPost<{ context_id: number }>("/api/contexts/get_or_create", draft)
        .then((r) => {
          onContextId(r.context_id);
          setCurrentContextId(r.context_id);
        })
        .catch((e) => {
          setErr(String(e));
        });
    }, 150);

    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [draft, onContextId]);

  // Load context label when context ID changes
  useEffect(() => {
    if (currentContextId === null) {
      setContextLabel("");
      return;
    }

    let alive = true;
    apiGet<{ label: string | null }>(`/api/contexts/${currentContextId}/label`)
      .then((result) => {
        if (!alive) return;
        setContextLabel(result.label || "");
      })
      .catch(() => {
        if (!alive) return;
        setContextLabel("");
      });

    return () => {
      alive = false;
    };
  }, [currentContextId]);

  // Jump to a saved context
  const jumpToContext = (ctx: ContextWithBindings) => {
    const header: ContextHeader = {
      daw_slot: ctx.daw_slot,
      preset_slot: ctx.preset_slot,
      port_id: ctx.port_id,
      channel: ctx.channel,
      bank_msb: ctx.bank_msb,
      bank_lsb: ctx.bank_lsb,
      program: ctx.program,
    };
    setDraft(header);
    onChange(header);
  };

  // Open save modal
  const openSaveModal = () => {
    if (currentContextId === null) {
      setSendStatus("No context selected");
      return;
    }
    setModalLabelInput(contextLabel || `DAW ${draft?.daw_slot} Preset ${draft?.preset_slot}`);
    setShowSaveModal(true);
  };

  // Save current context with a label
  const saveCurrentContext = async () => {
    if (currentContextId === null) return;

    const label = modalLabelInput.trim();
    if (!label) {
      setSendStatus("Please enter a label");
      return;
    }

    try {
      await apiPost(`/api/contexts/${currentContextId}/label`, { label });
      // Refresh contexts list to show new label
      await refreshContexts();
      setContextLabel(label);
      setShowSaveModal(false);
      setSendStatus("Context saved!");
      setTimeout(() => setSendStatus(""), 2000);
    } catch (e: unknown) {
      setSendStatus(errorMessage(e, "Save failed"));
    }
  };

  // Open Import/Export modal
  const openImportExportModal = async () => {
    if (currentContextId === null) {
      setImportExportStatus("No context selected");
      return;
    }

    setImportExportStatus("Loading...");
    setShowImportExportModal(true);

    try {
      // Fetch export JSON
      const exportData = await apiGet<ContextExport>(`/api/contexts/${currentContextId}/export`);
      setExportJson(JSON.stringify(exportData, null, 2));
      setImportExportStatus("");
    } catch (e: unknown) {
      setImportExportStatus(errorMessage(e, "Export failed"));
    }
  };

  // Copy export JSON to clipboard
  const copyExportJson = async () => {
    try {
      await navigator.clipboard.writeText(exportJson);
      setImportExportStatus("Copied to clipboard!");
      setTimeout(() => setImportExportStatus(""), 2000);
    } catch {
      setImportExportStatus("Failed to copy to clipboard");
    }
  };

  // Import context from JSON
  const importContext = async () => {
    if (!importJson.trim()) {
      setImportExportStatus("Please paste JSON to import");
      return;
    }

    setImportExportStatus("Importing...");

    try {
      const payload: unknown = JSON.parse(importJson);
      const result = await apiPost<{ ok: boolean; context_id: number; binding_count: number }>("/api/contexts/import", {
        payload,
        mode: importMode,
      });

      if (result.ok) {
        // Refresh contexts list
        await refreshContexts();

        // Switch to the imported context
        onContextId(result.context_id);
        setCurrentContextId(result.context_id);

        setImportExportStatus(`Imported ${result.binding_count} bindings!`);
        setTimeout(() => {
          setShowImportExportModal(false);
          setImportJson("");
          setImportExportStatus("");
        }, 1500);
      } else {
        setImportExportStatus("Import failed");
      }
    } catch (e: unknown) {
      setImportExportStatus(errorMessage(e, "Invalid JSON or import failed"));
    }
  };

  // Cascading helper functions - each filters by all PREVIOUS selections
  const hasBindingsForDaw = (dawSlot: number) =>
    contextsWithBindings.some((c) => c.daw_slot === dawSlot);

  const hasBindingsForPreset = (presetSlot: number) => {
    if (!draft) return false;
    return contextsWithBindings.some((c) => c.daw_slot === draft.daw_slot && c.preset_slot === presetSlot);
  };

  const hasBindingsForPort = (portId: number) => {
    if (!draft) return false;
    return contextsWithBindings.some(
      (c) => c.daw_slot === draft.daw_slot && c.preset_slot === draft.preset_slot && c.port_id === portId
    );
  };

  const hasBindingsForChannel = (channel: number) => {
    if (!draft) return false;
    return contextsWithBindings.some(
      (c) =>
        c.daw_slot === draft.daw_slot &&
        c.preset_slot === draft.preset_slot &&
        c.port_id === draft.port_id &&
        c.channel === channel
    );
  };

  const hasBindingsForBankMsb = (bankMsb: number) => {
    if (!draft) return false;
    return contextsWithBindings.some(
      (c) =>
        c.daw_slot === draft.daw_slot &&
        c.preset_slot === draft.preset_slot &&
        c.port_id === draft.port_id &&
        c.channel === draft.channel &&
        c.bank_msb === bankMsb
    );
  };

  const hasBindingsForBankLsb = (bankLsb: number) => {
    if (!draft) return false;
    return contextsWithBindings.some(
      (c) =>
        c.daw_slot === draft.daw_slot &&
        c.preset_slot === draft.preset_slot &&
        c.port_id === draft.port_id &&
        c.channel === draft.channel &&
        c.bank_msb === draft.bank_msb &&
        c.bank_lsb === bankLsb
    );
  };

  const hasBindingsForProgram = (program: number) => {
    if (!draft) return false;
    return contextsWithBindings.some(
      (c) =>
        c.daw_slot === draft.daw_slot &&
        c.preset_slot === draft.preset_slot &&
        c.port_id === draft.port_id &&
        c.channel === draft.channel &&
        c.bank_msb === draft.bank_msb &&
        c.bank_lsb === draft.bank_lsb &&
        c.program === program
    );
  };

  async function onSaveAsDefaults() {
    if (!draft) return;

    setErr("");
    setSendStatus("Saving…");

    try {
      await apiPost("/api/defaults/save", draft);
      setSendStatus("Saved as defaults");
      setTimeout(() => setSendStatus(""), 2000);
    } catch (e: unknown) {
      setSendStatus(errorMessage(e, "Save failed"));
    }
  }

  if (!draft) return <div style={{ padding: 12 }}>Loading ports…</div>;

  const disabled = !ports.length;

  // Get current context info for display
  const currentContext = contextsWithBindings.find(
    (ctx) =>
      ctx.daw_slot === draft.daw_slot &&
      ctx.preset_slot === draft.preset_slot &&
      ctx.port_id === draft.port_id &&
      ctx.channel === draft.channel &&
      ctx.bank_msb === draft.bank_msb &&
      ctx.bank_lsb === draft.bank_lsb &&
      ctx.program === draft.program
  );

  return (
    <div style={{ display: "grid", gap: 10 }}>
      {err ? (
        <div style={{ padding: 10, border: "1px solid tomato", color: "tomato", borderRadius: 8 }}>
          {err}
        </div>
      ) : null}

      {contextsLoadError ? (
        <div style={{ padding: 10, border: "1px solid tomato", color: "tomato", borderRadius: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{contextsLoadError}</span>
          <button onClick={refreshContexts} className="btn" style={{ padding: "4px 12px", fontSize: "12px" }}>
            Retry
          </button>
        </div>
      ) : null}

      {/* Saved Contexts Dropdown & Save Button */}
      <div style={{ display: "flex", gap: 10, alignItems: "center", padding: "10px", background: "rgba(0, 212, 255, 0.05)", borderRadius: "8px", border: "1px solid rgba(0, 212, 255, 0.2)" }}>
        {contextsWithBindings.length > 0 ? (
          <>
            <label style={{ display: "flex", gap: 8, alignItems: "center", flex: 1 }}>
              <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--accent)", minWidth: "max-content" }}>
                Saved Contexts:
              </span>
              <select
                value={currentContext ? currentContext.id : ""}
                onChange={(e) => {
                  const ctx = contextsWithBindings.find((c) => c.id === Number(e.target.value));
                  if (ctx) jumpToContext(ctx);
                }}
                style={{ flex: 1 }}
              >
                <option value="" disabled>
                  {currentContext ? currentContext.label || "Current (unlabeled)" : "Select a saved context..."}
                </option>
                {contextsWithBindings.map((ctx) => {
                  const label =
                    ctx.label ||
                    `D${ctx.daw_slot} P${ctx.preset_slot} Port${ctx.port_id} Ch${ctx.channel + 1} M${ctx.bank_msb} L${ctx.bank_lsb} Prg${ctx.program}`;
                  return (
                    <option key={ctx.id} value={ctx.id}>
                      {label} ({ctx.binding_count} binding{ctx.binding_count !== 1 ? "s" : ""}, ch {ctx.channel + 1})
                    </option>
                  );
                })}
              </select>
            </label>
            <button
              onClick={openSaveModal}
              className="btn-secondary"
              style={{ fontSize: "12px", padding: "8px 16px", minWidth: "max-content" }}
              title="Save current context with a custom name"
            >
              {currentContext?.label ? "Rename Context" : "Save Context As..."}
            </button>
            <button
              onClick={openImportExportModal}
              className="btn"
              style={{ fontSize: "12px", padding: "8px 16px", minWidth: "max-content" }}
              disabled={currentContextId === null}
              title="Import or export context bindings"
            >
              Import/Export
            </button>
            <button
              onClick={refreshContexts}
              className="btn"
              style={{ fontSize: "12px", padding: "8px 16px", minWidth: "max-content" }}
              title="Refresh contexts list"
            >
              ⟳ Refresh
            </button>
          </>
        ) : (
          <>
            <div style={{ flex: 1, fontSize: "12px", opacity: 0.7 }}>
              No saved contexts yet. Configure your settings below and click &quot;Save Context As...&quot; to remember them.
            </div>
            <button
              onClick={openSaveModal}
              className="btn-secondary"
              style={{ fontSize: "12px", padding: "8px 16px", minWidth: "max-content" }}
              disabled={currentContextId === null}
              title="Save current context with a custom name"
            >
              Save Context As...
            </button>
            <button
              onClick={openImportExportModal}
              className="btn"
              style={{ fontSize: "12px", padding: "8px 16px", minWidth: "max-content" }}
              disabled={currentContextId === null}
              title="Import or export context bindings"
            >
              Import/Export
            </button>
            <button
              onClick={refreshContexts}
              className="btn"
              style={{ fontSize: "12px", padding: "8px 16px", minWidth: "max-content" }}
              title="Refresh contexts list"
            >
              ⟳ Refresh
            </button>
          </>
        )}
      </div>

      {/* Show current context status */}
      {currentContextId !== null && draft && (
        <div style={{ fontSize: "11px", opacity: 0.7, padding: "4px 8px" }}>
          Current: {contextLabel || `Context #${currentContextId} (no label)`}
          {currentContext && ` • ${currentContext.binding_count} binding${currentContext.binding_count !== 1 ? "s" : ""}`}
          {` • ch ${draft.channel + 1}`}
        </div>
      )}

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
              <option key={n} value={n} className={hasBindingsForDaw(n) ? "has-bindings" : ""}>
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
              <option key={n} value={n} className={hasBindingsForPreset(n) ? "has-bindings" : ""}>
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
              <option key={p.id} value={p.id} className={hasBindingsForPort(p.id) ? "has-bindings" : ""}>
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
              <option key={n} value={n} className={hasBindingsForChannel(n) ? "has-bindings" : ""}>
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
              <option key={n} value={n} className={hasBindingsForBankMsb(n) ? "has-bindings" : ""}>
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
              <option key={n} value={n} className={hasBindingsForBankLsb(n) ? "has-bindings" : ""}>
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
              <option key={n} value={n} className={hasBindingsForProgram(n) ? "has-bindings" : ""}>
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

      {/* Save Context Modal */}
      <Modal
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        title={currentContext?.label ? "Rename Context" : "Save Context As..."}
      >
        <div style={{ display: "grid", gap: 16 }}>
          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: 500, marginBottom: "8px", opacity: 0.9 }}>
              Context Name
            </label>
            <input
              type="text"
              value={modalLabelInput}
              onChange={(e) => setModalLabelInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  saveCurrentContext();
                }
              }}
              placeholder="e.g., Ableton Live - Default"
              autoFocus
              style={{ width: "100%", fontSize: "14px" }}
            />
            <div style={{ fontSize: "11px", opacity: 0.6, marginTop: "6px" }}>
              Give this configuration a memorable name so you can find it later.
            </div>
          </div>

          {/* Current context details */}
          {draft && (
            <div
              style={{
                padding: "12px",
                background: "rgba(255, 255, 255, 0.03)",
                borderRadius: "6px",
                border: "1px solid rgba(255, 255, 255, 0.1)",
              }}
            >
              <div style={{ fontSize: "11px", opacity: 0.6, marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                Configuration Details
              </div>
              <div style={{ fontSize: "12px", fontFamily: "monospace", lineHeight: 1.6 }}>
                <div>DAW: {draft.daw_slot}</div>
                <div>Preset: {draft.preset_slot}</div>
                <div>Port: {draft.port_id}</div>
                <div>Channel: {draft.channel + 1}</div>
                <div>
                  Bank: MSB={draft.bank_msb} LSB={draft.bank_lsb}
                </div>
                <div>Program: {draft.program}</div>
              </div>
            </div>
          )}

          {/* Buttons */}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button onClick={() => setShowSaveModal(false)} className="btn" style={{ padding: "8px 20px" }}>
              Cancel
            </button>
            <button onClick={saveCurrentContext} className="btn-secondary" style={{ padding: "8px 20px" }}>
              {currentContext?.label ? "Rename" : "Save"}
            </button>
          </div>
        </div>
      </Modal>

      {/* Import/Export Modal */}
      <Modal
        isOpen={showImportExportModal}
        onClose={() => {
          setShowImportExportModal(false);
          setImportJson("");
          setImportExportStatus("");
        }}
        title="Import/Export Context"
      >
        <div style={{ display: "grid", gap: 20 }}>
          {/* Status message */}
          {importExportStatus && (
            <div
              style={{
                padding: "10px",
                background: "rgba(0, 212, 255, 0.1)",
                border: "1px solid rgba(0, 212, 255, 0.3)",
                borderRadius: "6px",
                fontSize: "13px",
                textAlign: "center",
              }}
            >
              {importExportStatus}
            </div>
          )}

          {/* Export Section */}
          <div>
            <div style={{ fontSize: "14px", fontWeight: 600, marginBottom: "8px", color: "var(--accent)" }}>
              Export Current Context
            </div>
            <div style={{ fontSize: "12px", opacity: 0.7, marginBottom: "10px" }}>
              Copy the JSON below to back up or share this context configuration.
            </div>
            <textarea
              value={exportJson}
              readOnly
              style={{
                width: "100%",
                height: "150px",
                fontSize: "11px",
                fontFamily: "monospace",
                resize: "vertical",
                background: "rgba(0, 0, 0, 0.3)",
                border: "1px solid rgba(255, 255, 255, 0.2)",
                borderRadius: "4px",
                padding: "10px",
              }}
            />
            <button
              onClick={copyExportJson}
              className="btn-secondary"
              style={{ marginTop: "8px", fontSize: "13px", padding: "8px 16px" }}
            >
              Copy to Clipboard
            </button>
          </div>

          {/* Divider */}
          <div style={{ height: "1px", background: "rgba(255, 255, 255, 0.1)" }} />

          {/* Import Section */}
          <div>
            <div style={{ fontSize: "14px", fontWeight: 600, marginBottom: "8px", color: "var(--accent)" }}>
              Import Context
            </div>
            <div style={{ fontSize: "12px", opacity: 0.7, marginBottom: "10px" }}>
              Paste exported JSON to restore or load a context configuration.
            </div>
            <textarea
              value={importJson}
              onChange={(e) => setImportJson(e.target.value)}
              placeholder='Paste exported JSON here (e.g., {"version": 1, "context": {...}, "bindings": [...]})'
              style={{
                width: "100%",
                height: "150px",
                fontSize: "11px",
                fontFamily: "monospace",
                resize: "vertical",
                background: "rgba(0, 0, 0, 0.3)",
                border: "1px solid rgba(255, 255, 255, 0.2)",
                borderRadius: "4px",
                padding: "10px",
              }}
            />

            {/* Import mode selection */}
            <div style={{ marginTop: "12px", display: "flex", gap: 16, alignItems: "center" }}>
              <label style={{ fontSize: "13px", display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
                <input
                  type="radio"
                  name="import-mode"
                  value="merge"
                  checked={importMode === "merge"}
                  onChange={() => setImportMode("merge")}
                />
                <span>Merge (keep existing bindings)</span>
              </label>
              <label style={{ fontSize: "13px", display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
                <input
                  type="radio"
                  name="import-mode"
                  value="replace"
                  checked={importMode === "replace"}
                  onChange={() => setImportMode("replace")}
                />
                <span>Replace (delete existing bindings)</span>
              </label>
            </div>

            <button
              onClick={importContext}
              className="btn-secondary"
              style={{ marginTop: "12px", fontSize: "13px", padding: "8px 16px" }}
            >
              Import
            </button>
          </div>

          {/* Close button */}
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "8px" }}>
            <button
              onClick={() => {
                setShowImportExportModal(false);
                setImportJson("");
                setImportExportStatus("");
              }}
              className="btn"
              style={{ padding: "8px 20px" }}
            >
              Close
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
