"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "./useMidiApi";
import type { Binding } from "./types";

type Props = {
  contextId: number | null;
  selectedNote: number | null;
  onBindingsChanged: () => void;
};

export function BindingEditor({ contextId, selectedNote, onBindingsChanged }: Props) {
  const [command, setCommand] = useState<string>("");
  const [debounceMs, setDebounceMs] = useState<number>(200);
  const [requireArmed, setRequireArmed] = useState<number>(1);
  const [enabled, setEnabled] = useState<number>(1);
  const [notes, setNotes] = useState<string>("");
  const [notifyText, setNotifyText] = useState<string>("");
  const [notifyEmoji, setNotifyEmoji] = useState<string>("");
  const [bindingId, setBindingId] = useState<number | null>(null);
  const [status, setStatus] = useState<string>("");
  const [showEmojiPicker, setShowEmojiPicker] = useState<boolean>(false);

  const canAct = contextId != null && selectedNote != null;

  const emojiPalette = ["✅", "⚡", "🔥", "🎛️", "🎹", "🧠", "📁", "🌐", "🧰", "🖥️", "🎬", "🎵", "🧪", "🧩", "⭐"];

  // Auto-load binding when note is selected
  useEffect(() => {
    if (!canAct) return;

    let alive = true;

    async function loadBinding() {
      setStatus("Loading…");
      try {
        const list = await apiGet<any[]>(`/api/contexts/${contextId}/bindings`);
        if (!alive) return;

        const match = list.find((b) => b.trig_type === 1 && b.note === selectedNote);
        if (!match) {
          setCommand("");
          setDebounceMs(200);
          setRequireArmed(1);
          setEnabled(1);
          setNotes("");
          setNotifyText("");
          setNotifyEmoji("");
          setBindingId(null);
          setStatus("No binding for this note");
          return;
        }

        setCommand(match.command ?? "");
        setDebounceMs(match.debounce_ms ?? 200);
        setRequireArmed(match.require_armed ?? 1);
        setEnabled(match.enabled ?? 1);
        setNotes(match.notes ?? "");
        setNotifyText(match.notify_text ?? "");
        setNotifyEmoji(match.notify_emoji ?? "");
        setBindingId(match.id);
        setStatus(`Loaded binding id=${match.id}`);
      } catch (err) {
        if (!alive) return;
        setStatus(`Error loading: ${err}`);
      }
    }

    loadBinding();

    return () => {
      alive = false;
    };
  }, [contextId, selectedNote, canAct]);

  async function getExisting() {
    if (!canAct) return;
    setStatus("Loading binding…");
    const list = await apiGet<any[]>(`/api/contexts/${contextId}/bindings`);
    const match = list.find((b) => b.trig_type === 1 && b.note === selectedNote);
    if (!match) {
      setCommand("");
      setDebounceMs(200);
      setRequireArmed(1);
      setEnabled(1);
      setNotes("");
      setNotifyText("");
      setNotifyEmoji("");
      setBindingId(null);
      setStatus("No binding found for that note.");
      return;
    }
    setCommand(match.command ?? "");
    setDebounceMs(match.debounce_ms ?? 200);
    setRequireArmed(match.require_armed ?? 1);
    setEnabled(match.enabled ?? 1);
    setNotes(match.notes ?? "");
    setNotifyText(match.notify_text ?? "");
    setNotifyEmoji(match.notify_emoji ?? "");
    setBindingId(match.id);
    setStatus(`Loaded binding id=${match.id}`);
  }

  async function setBinding() {
    if (!canAct) return;
    if (!command.trim()) {
      setStatus("Command is empty.");
      return;
    }
    setStatus("Saving…");
    const payload = {
      context_id: contextId!,
      enabled,
      trig_type: 1,
      note: selectedNote!,
      cc: null,
      command,
      debounce_ms: debounceMs,
      require_armed: requireArmed,
      notes,
      notify_text: notifyText,
      notify_emoji: notifyEmoji.slice(0, 8), // Limit emoji to 8 chars
    };
    await apiPost("/api/bindings/set", payload);
    setStatus("Saved.");
    onBindingsChanged();
  }

  async function removeBinding() {
    if (!canAct) return;
    setStatus("Removing…");
    // this endpoint in our FastAPI example takes query params; easiest is add a JSON body later.
    // For now use POST with query args:
    await fetch(
      `http://127.0.0.1:8765/api/bindings/remove?context_id=${contextId}&trig_type=1&note=${selectedNote}`,
      { method: "POST" }
    );
    setCommand("");
    setNotes("");
    setNotifyText("");
    setNotifyEmoji("");
    setBindingId(null);
    setStatus("Removed.");
    onBindingsChanged();
  }

  async function testRun() {
    if (bindingId === null) {
      setStatus("No binding loaded to test.");
      return;
    }
    setStatus("Running command…");
    try {
      const result = await apiPost<{ ok?: boolean; pid?: number; error?: string }>("/api/bindings/run", { binding_id: bindingId });
      if (result?.ok) {
        setStatus(`Command started (PID: ${result.pid})`);
      } else {
        setStatus(`Error: ${result?.error ?? "Unknown error"}`);
      }
    } catch (err) {
      setStatus(`Failed to run: ${err}`);
    }
  }

  return (
    <div style={{ border: "1px solid #333", padding: 12, borderRadius: 12 }}>
      <div style={{ marginBottom: 8, opacity: 0.8 }}>
        Selected: {selectedNote == null ? "—" : `note ${selectedNote}`} | Context: {contextId ?? "—"}
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <button className="btn-secondary" disabled={!canAct} onClick={setBinding}>Save</button>
        <button className="btn-danger" disabled={!canAct} onClick={removeBinding}>Remove</button>
        <button className="btn-primary" disabled={bindingId === null} onClick={testRun}>Run Now</button>
      </div>

      <label style={{ display: "block", marginBottom: 8 }}>
        Command
        <input
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          placeholder="e.g. firefox 'google.com'"
          style={{ width: "100%", padding: 8, marginTop: 4 }}
        />
      </label>

      <label style={{ display: "block", marginBottom: 8 }}>
        Emoji (for note grid marker)
        <div style={{ display: "flex", gap: 8, marginTop: 4, position: "relative" }}>
          <input
            value={notifyEmoji}
            onChange={(e) => setNotifyEmoji(e.target.value.slice(0, 8))}
            placeholder="e.g. 🎵 or leave empty for •"
            maxLength={8}
            style={{ flex: 1, padding: 8 }}
          />
          <button
            type="button"
            onClick={() => setShowEmojiPicker(!showEmojiPicker)}
            style={{ padding: "8px 12px", whiteSpace: "nowrap" }}
          >
            {showEmojiPicker ? "Close" : "Pick Emoji"}
          </button>

          {showEmojiPicker && (
            <div
              style={{
                position: "absolute",
                top: "calc(100% + 4px)",
                right: 0,
                background: "rgba(20, 20, 20, 0.95)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                borderRadius: 10,
                padding: 12,
                display: "grid",
                gridTemplateColumns: "repeat(5, 1fr)",
                gap: 8,
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.6)",
                backdropFilter: "blur(10px)",
                zIndex: 50,
              }}
            >
              {emojiPalette.map((emoji) => (
                <button
                  key={emoji}
                  type="button"
                  onClick={() => {
                    setNotifyEmoji(emoji);
                    setShowEmojiPicker(false);
                  }}
                  style={{
                    padding: 8,
                    fontSize: 20,
                    cursor: "pointer",
                    background: "rgba(255, 255, 255, 0.05)",
                    border: "1px solid rgba(255, 255, 255, 0.1)",
                    borderRadius: 6,
                    transition: "all 0.15s",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "rgba(0, 212, 255, 0.2)";
                    e.currentTarget.style.transform = "scale(1.1)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
                    e.currentTarget.style.transform = "scale(1)";
                  }}
                >
                  {emoji}
                </button>
              ))}
              <div
                style={{
                  gridColumn: "1 / -1",
                  marginTop: 4,
                  fontSize: 11,
                  opacity: 0.6,
                  textAlign: "center",
                }}
              >
                Or paste any emoji
              </div>
            </div>
          )}
        </div>
      </label>

      <label style={{ display: "block", marginBottom: 8 }}>
        Notify Text
        <input
          value={notifyText}
          onChange={(e) => setNotifyText(e.target.value)}
          placeholder="Notification message when triggered"
          style={{ width: "100%", padding: 8, marginTop: 4 }}
        />
      </label>

      <label style={{ display: "block", marginBottom: 8 }}>
        Notes
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Freeform notes for this binding"
          rows={4}
          style={{ width: "100%", padding: 8, marginTop: 4, resize: "vertical" }}
        />
      </label>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <label style={{ display: "flex", alignItems: "center" }}>
          Debounce (ms)
          <span className="tooltip">
            ⓘ
            <span className="tooltip-content">Minimum time between triggers for this binding</span>
          </span>
          <input
            type="number"
            min={0}
            max={5000}
            value={debounceMs}
            onChange={(e) => setDebounceMs(Number(e.target.value))}
            style={{ width: 120, marginLeft: 8 }}
          />
        </label>

        <label style={{ display: "flex", alignItems: "center" }}>
          Require Keygrab
          <span className="tooltip">
            ⓘ
            <span className="tooltip-content">Only trigger when Keygrab is ON</span>
          </span>
          <select value={requireArmed} onChange={(e) => setRequireArmed(Number(e.target.value))} style={{ marginLeft: 8 }}>
            <option value={1}>Yes</option>
            <option value={0}>No</option>
          </select>
        </label>

        <label style={{ display: "flex", alignItems: "center" }}>
          Active
          <span className="tooltip">
            ⓘ
            <span className="tooltip-content">If OFF, this binding will not run</span>
          </span>
          <select value={enabled} onChange={(e) => setEnabled(Number(e.target.value))} style={{ marginLeft: 8 }}>
            <option value={1}>Yes</option>
            <option value={0}>No</option>
          </select>
        </label>
      </div>

      <div style={{ marginTop: 10, opacity: 0.8 }}>{status}</div>
    </div>
  );
}

