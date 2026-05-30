"use client";

import { ToggleSwitch } from "../ToggleSwitch";
import type { AutomationState } from "../v2/types";
import type { BackendMidiStatus, BackendPort } from "../v2/api";

type Props = {
  automation: AutomationState;
  selectedInputPort: string | null;
  inputPorts: BackendPort[];
  midiStatus: BackendMidiStatus | null;
  dataSourceLabel: string;
  onAutomationArmedChange?: (armed: boolean) => void;
  onKeygrabChange?: (enabled: boolean) => void;
  onMouseModeChange?: (mouseMode: boolean) => void;
  onSelectedInputPortChange?: (portName: string | null) => void;
};

const PANEL = "rounded-md border border-white/8 bg-white/[0.014] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.018),inset_0_0_24px_rgba(0,0,0,0.18)]";
const HEADER = "mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/65";

function SettingRow({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="py-1.5">
      <div className="flex items-center justify-between gap-4">
        <span className="text-[12px] text-white/75">{label}</span>
        <div className="shrink-0">{children}</div>
      </div>
      {hint && (
        <p className="mt-1 text-[10.5px] leading-relaxed text-white/40">{hint}</p>
      )}
    </div>
  );
}

export function SettingsPanel({
  automation,
  selectedInputPort,
  inputPorts,
  midiStatus,
  dataSourceLabel,
  onAutomationArmedChange,
  onKeygrabChange,
  onMouseModeChange,
  onSelectedInputPortChange,
}: Props) {
  const hasPorts = inputPorts.length > 0;
  const midiOk = midiStatus?.available !== false && midiStatus?.degraded !== true;

  return (
    <div className="space-y-2.5">
      {/* MIDI Input */}
      <section className={PANEL}>
        <h3 className={HEADER}>MIDI Input</h3>
        <div className="space-y-2">
          <div>
            <label className="mb-1 block text-[10px] uppercase tracking-[0.12em] text-white/45">
              Device
            </label>
            <select
              aria-label="MIDI input"
              className="w-full !h-7 !rounded !border-white/10 !bg-black/40 !px-2 !py-0 !text-[11px] text-white/85"
              value={selectedInputPort ?? ""}
              onChange={(event) => onSelectedInputPortChange?.(event.target.value || null)}
            >
              <option value="">{hasPorts ? "All Inputs" : "No MIDI device"}</option>
              {inputPorts.map((port) => (
                <option key={port.name} value={port.name} className="bg-zinc-900">
                  {port.online === false ? `${port.name} (offline)` : port.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={[
                "inline-flex items-center rounded border !px-1.5 !py-px text-[9.5px] uppercase tracking-[0.12em]",
                midiOk
                  ? "border-emerald-300/25 bg-emerald-400/[0.06] text-emerald-100"
                  : "border-amber-300/25 bg-amber-400/[0.06] text-amber-100",
              ].join(" ")}
            >
              {midiStatus?.message ?? (midiOk ? "Available" : "Unavailable")}
            </span>
            <span className="font-mono text-[10px] text-white/45">{dataSourceLabel}</span>
          </div>
        </div>
      </section>

      {/* Automation */}
      <section className={PANEL}>
        <h3 className={HEADER}>Automation</h3>
        <div className="divide-y divide-white/[0.06]">
          <SettingRow
            label="Automation Armed"
            hint="When armed, MIDI input triggers bound commands. When disarmed, bindings are suspended but not deleted."
          >
            <ToggleSwitch
              on={automation.armed}
              onClick={onAutomationArmedChange ? () => onAutomationArmedChange(!automation.armed) : undefined}
            />
          </SettingRow>
        </div>
      </section>

      {/* Input Behavior */}
      <section className={PANEL}>
        <h3 className={HEADER}>Input Behavior</h3>
        <div className="divide-y divide-white/[0.06]">
          <SettingRow
            label="Keyboard Capture (Keygrab)"
            hint="Captures keyboard shortcuts globally so key presses are routed to the mapper instead of the focused app."
          >
            <ToggleSwitch
              on={automation.keygrab}
              onClick={onKeygrabChange ? () => onKeygrabChange(!automation.keygrab) : undefined}
            />
          </SettingRow>
          <SettingRow
            label="Mouse Mode"
            hint="When enabled, clicking a note tile or CC bar populates the Quick Bind form. When disabled, tile clicks are inactive."
          >
            <ToggleSwitch
              on={automation.mouseMode}
              onClick={onMouseModeChange ? () => onMouseModeChange(!automation.mouseMode) : undefined}
            />
          </SettingRow>
        </div>
      </section>
    </div>
  );
}
