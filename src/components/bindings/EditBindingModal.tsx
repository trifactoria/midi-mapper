"use client";

import { useEffect, useState } from "react";
import { IconPicker } from "../IconPicker";
import type { BackendBindingPatch } from "../v2/api";
import type { V2BindingSummary } from "../v2/types";

const COLORS = ["cyan", "emerald", "violet", "amber", "rose", "blue", "slate", "purple", "orange", "red"] as const;
const COLOR_HEX: Record<string, string> = {
  cyan: "#22d3ee", emerald: "#34d399", violet: "#a78bfa", amber: "#fbbf24",
  rose: "#fb7185", blue: "#60a5fa", slate: "#94a3b8", purple: "#c084fc",
  orange: "#fb923c", red: "#f87171",
};

type FormState = {
  eventType: "note_on" | "control_change";
  channel: number;
  note: number;
  controller: number;
  velocityMin: number;
  velocityMax: number;
  valueMin: number;
  valueMax: number;
  command: string;
  workingDirectory: string;
  executionMode: "argv" | "detached";
  timeoutMs: number;
  enabled: boolean;
  requireArmed: boolean;
  cooldownMs: number;
  displayLabel: string;
  displayColor: string;
  displayIcon: string;
  notes: string;
};

function fromBinding(b: V2BindingSummary): FormState {
  return {
    eventType: b.kind === "cc" ? "control_change" : "note_on",
    channel: b.channel ?? 0,
    note: b.note ?? 60,
    controller: b.controller ?? 0,
    velocityMin: b.velocityMin ?? 0,
    velocityMax: b.velocityMax ?? 127,
    valueMin: b.valueMin ?? 0,
    valueMax: b.valueMax ?? 127,
    command: b.command,
    workingDirectory: b.workingDirectory ?? "",
    executionMode: b.executionMode === "detached" ? "detached" : "argv",
    timeoutMs: b.timeoutMs ?? 5000,
    enabled: b.enabled,
    requireArmed: b.requireArmed,
    cooldownMs: b.cooldownMs ?? 200,
    displayLabel: b.displayLabel ?? "",
    displayColor: b.displayColor ?? "",
    displayIcon: b.icon ?? "",
    notes: b.notes ?? "",
  };
}

function buildPatch(form: FormState): BackendBindingPatch {
  const trigger: BackendBindingPatch["trigger"] = {
    event_type: form.eventType,
    channel: form.channel,
    ...(form.eventType === "note_on"
      ? { note: form.note, velocity_min: form.velocityMin, velocity_max: form.velocityMax }
      : { controller: form.controller, value_min: form.valueMin, value_max: form.valueMax }),
  };
  return {
    enabled: form.enabled ? 1 : 0,
    require_armed: form.requireArmed ? 1 : 0,
    cooldown_ms: form.cooldownMs,
    notes: form.notes,
    display_label: form.displayLabel,
    display_color: form.displayColor,
    display_icon: form.displayIcon || undefined,
    trigger,
    action: {
      command: form.command,
      working_directory: form.workingDirectory || undefined,
      execution_mode: form.executionMode,
      timeout_ms: form.timeoutMs || undefined,
    },
  };
}

type Props = {
  binding: V2BindingSummary;
  onSave: (bindingId: string, patch: BackendBindingPatch) => Promise<void>;
  onCancel: () => void;
};

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="block text-[10px] font-semibold uppercase tracking-[0.12em] text-white/40">
      {children}
    </span>
  );
}

function inputCls(extra = "") {
  return `w-full rounded border border-white/10 bg-white/[0.05] px-2 py-1 text-[11.5px] text-white/90 placeholder-white/25 focus:border-white/20 focus:outline-none ${extra}`;
}

export function EditBindingModal({ binding, onSave, onCancel }: Props) {
  const [form, setForm] = useState<FormState>(() => fromBinding(binding));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function numInput(value: number, onChange: (v: number) => void, min = 0, max = 127) {
    return (
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Math.min(max, Math.max(min, Number(e.target.value) || 0)))}
        className={inputCls("w-20 tabular-nums")}
      />
    );
  }

  async function handleSave() {
    if (!form.command.trim()) { setError("Command is required"); return; }
    setSaving(true);
    setError(null);
    try {
      await onSave(binding.id, buildPatch(form));
      onCancel();
    } catch {
      setError("Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/65 backdrop-blur-sm"
      onClick={onCancel}
    >
      <div
        className="relative my-6 w-full max-w-[480px] rounded-lg border border-white/12 bg-zinc-900 shadow-[0_16px_48px_rgba(0,0,0,0.7)]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/[0.08] px-4 py-3">
          <h2 className="text-[12.5px] font-semibold text-white/90">Edit Binding</h2>
          <button
            type="button"
            onClick={onCancel}
            className="grid !h-6 !w-6 place-items-center rounded border border-white/10 text-white/50 hover:text-white/80"
            style={{ background: "rgba(255,255,255,0.04)" }}
          >
            <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M4 4l8 8M12 4l-8 8" />
            </svg>
          </button>
        </div>

        <div className="space-y-4 px-4 py-4">
          {/* MIDI Trigger */}
          <section>
            <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/45">MIDI Trigger</h3>
            <div className="space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <FieldLabel>Event Type</FieldLabel>
                  <select
                    value={form.eventType}
                    onChange={(e) => set("eventType", e.target.value as "note_on" | "control_change")}
                    className={inputCls()}
                  >
                    <option value="note_on">Note On</option>
                    <option value="control_change">Control Change</option>
                  </select>
                </div>
                <div>
                  <FieldLabel>Channel (0–15)</FieldLabel>
                  {numInput(form.channel, (v) => set("channel", v), 0, 15)}
                </div>
              </div>
              {form.eventType === "note_on" ? (
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <FieldLabel>Note (0–127)</FieldLabel>
                    {numInput(form.note, (v) => set("note", v))}
                  </div>
                  <div>
                    <FieldLabel>Velocity Min / Max</FieldLabel>
                    <div className="flex items-center gap-1">
                      {numInput(form.velocityMin, (v) => set("velocityMin", Math.min(v, form.velocityMax)))}
                      <span className="text-white/30">–</span>
                      {numInput(form.velocityMax, (v) => set("velocityMax", Math.max(v, form.velocityMin)))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <FieldLabel>Controller (0–127)</FieldLabel>
                    {numInput(form.controller, (v) => set("controller", v))}
                  </div>
                  <div>
                    <FieldLabel>Value Min / Max</FieldLabel>
                    <div className="flex items-center gap-1">
                      {numInput(form.valueMin, (v) => set("valueMin", Math.min(v, form.valueMax)))}
                      <span className="text-white/30">–</span>
                      {numInput(form.valueMax, (v) => set("valueMax", Math.max(v, form.valueMin)))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>

          <div className="border-t border-white/[0.06]" />

          {/* Command */}
          <section>
            <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/45">Command</h3>
            <div className="space-y-2">
              <div>
                <FieldLabel>Command</FieldLabel>
                <input
                  type="text"
                  value={form.command}
                  onChange={(e) => set("command", e.target.value)}
                  placeholder="e.g. notify-send 'Hello'"
                  className={inputCls("font-mono text-[11px]")}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <FieldLabel>Working Directory</FieldLabel>
                  <input
                    type="text"
                    value={form.workingDirectory}
                    onChange={(e) => set("workingDirectory", e.target.value)}
                    placeholder="/home/user"
                    className={inputCls("font-mono text-[10.5px]")}
                  />
                </div>
                <div>
                  <FieldLabel>Execution Mode</FieldLabel>
                  <select
                    value={form.executionMode}
                    onChange={(e) => set("executionMode", e.target.value as "argv" | "detached")}
                    className={inputCls()}
                  >
                    <option value="argv">Blocking</option>
                    <option value="detached">Detached</option>
                  </select>
                </div>
              </div>
              {form.executionMode === "argv" && (
                <div className="w-36">
                  <FieldLabel>Timeout (ms)</FieldLabel>
                  {numInput(form.timeoutMs, (v) => set("timeoutMs", v), 0, 300000)}
                </div>
              )}
            </div>
          </section>

          <div className="border-t border-white/[0.06]" />

          {/* Behavior */}
          <section>
            <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/45">Behavior</h3>
            <div className="flex flex-wrap items-center gap-4">
              <label className="flex cursor-pointer items-center gap-2 text-[11.5px] text-white/75">
                <input
                  type="checkbox"
                  checked={form.enabled}
                  onChange={(e) => set("enabled", e.target.checked)}
                  className="rounded"
                />
                Enabled
              </label>
              <label className="flex cursor-pointer items-center gap-2 text-[11.5px] text-white/75">
                <input
                  type="checkbox"
                  checked={form.requireArmed}
                  onChange={(e) => set("requireArmed", e.target.checked)}
                  className="rounded"
                />
                Require Armed
              </label>
              <div className="flex items-center gap-2">
                <FieldLabel>Cooldown</FieldLabel>
                <div className="w-24">
                  {numInput(form.cooldownMs, (v) => set("cooldownMs", v), 0, 60000)}
                </div>
                <span className="text-[10.5px] text-white/40">ms</span>
              </div>
            </div>
          </section>

          <div className="border-t border-white/[0.06]" />

          {/* Display */}
          <section>
            <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/45">Display</h3>
            <div className="space-y-2">
              <div>
                <FieldLabel>Label</FieldLabel>
                <input
                  type="text"
                  value={form.displayLabel}
                  onChange={(e) => set("displayLabel", e.target.value)}
                  placeholder="Optional display label"
                  className={inputCls()}
                />
              </div>
              <div>
                <FieldLabel>Icon</FieldLabel>
                <div className="mt-1">
                  <IconPicker value={form.displayIcon} onChange={(v) => set("displayIcon", v)} />
                </div>
              </div>
              <div>
                <FieldLabel>Color</FieldLabel>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  <button
                    type="button"
                    onClick={() => set("displayColor", "")}
                    className={[
                      "h-5 w-5 rounded-full border",
                      form.displayColor === ""
                        ? "border-white/50 bg-white/[0.12]"
                        : "border-white/20 bg-white/[0.05] hover:bg-white/[0.10]",
                    ].join(" ")}
                    title="No color"
                  />
                  {COLORS.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => set("displayColor", c)}
                      className={[
                        "h-5 w-5 rounded-full border-2 transition",
                        form.displayColor === c ? "border-white/80 scale-110" : "border-transparent hover:border-white/30",
                      ].join(" ")}
                      style={{ backgroundColor: COLOR_HEX[c] }}
                      title={c}
                    />
                  ))}
                </div>
              </div>
              <div>
                <FieldLabel>Notes</FieldLabel>
                <textarea
                  value={form.notes}
                  onChange={(e) => set("notes", e.target.value)}
                  rows={2}
                  placeholder="Optional notes about this binding"
                  className={inputCls("resize-none")}
                />
              </div>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-white/[0.08] px-4 py-3">
          <span className="text-[11px] text-rose-300/80">{error ?? ""}</span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onCancel}
              disabled={saving}
              className="rounded border border-white/10 !px-3 !py-1.5 !text-[11.5px] text-white/65 hover:text-white/90 disabled:opacity-40"
              style={{ background: "rgba(255,255,255,0.04)" }}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={saving}
              className="rounded border border-cyan-400/25 !px-3 !py-1.5 !text-[11.5px] text-cyan-200 hover:text-cyan-100 disabled:opacity-40"
              style={{ background: "rgba(0,200,230,0.10)" }}
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
