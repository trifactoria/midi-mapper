"use client";

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

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/65">
      {children}
    </h3>
  );
}

function SettingRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2">
      <span className="text-[12px] text-white/75">{label}</span>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

function Toggle({ on, onClick }: { on: boolean; onClick?: () => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      onClick={onClick}
      className={[
        "relative inline-flex h-5 w-9 shrink-0 rounded-full border transition",
        on
          ? "border-emerald-300/40 bg-emerald-400/80 shadow-[0_0_10px_rgba(52,211,153,0.35)]"
          : "border-white/15 bg-white/[0.08]",
        onClick ? "cursor-pointer" : "cursor-default opacity-50",
      ].join(" ")}
    >
      <span
        className={[
          "absolute top-0.5 h-3.5 w-3.5 rounded-full bg-white transition",
          on ? "left-[18px]" : "left-0.5",
        ].join(" ")}
      />
    </button>
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
    <div className="space-y-4">
      {/* MIDI Input */}
      <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
        <SectionHeader>MIDI Input</SectionHeader>
        <div className="divide-y divide-white/[0.06]">
          <SettingRow label="Input device">
            <select
              aria-label="MIDI input"
              className="!h-7 !rounded !border-white/10 !bg-black/40 !px-2 !py-0 !text-[11px] text-white/85"
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
          </SettingRow>
          <SettingRow label="MIDI status">
            <span className={["text-[11px] font-mono", midiOk ? "text-emerald-300/80" : "text-amber-300/80"].join(" ")}>
              {midiStatus?.message ?? (midiOk ? "Available" : "Unavailable")}
            </span>
          </SettingRow>
          <SettingRow label="Data source">
            <span className="text-[11px] font-mono text-white/55">{dataSourceLabel}</span>
          </SettingRow>
        </div>
      </section>

      {/* Automation */}
      <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
        <SectionHeader>Automation</SectionHeader>
        <div className="divide-y divide-white/[0.06]">
          <SettingRow label="Automation Armed">
            <Toggle on={automation.armed} onClick={onAutomationArmedChange ? () => onAutomationArmedChange(!automation.armed) : undefined} />
          </SettingRow>
          <div className="py-2 text-[10.5px] leading-relaxed text-white/40">
            When armed, MIDI input triggers bound commands. When disarmed, bindings are suspended but not deleted.
          </div>
        </div>
      </section>

      {/* Input behavior */}
      <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
        <SectionHeader>Input Behavior</SectionHeader>
        <div className="divide-y divide-white/[0.06]">
          <SettingRow label="Keyboard Capture (Keygrab)">
            <Toggle on={automation.keygrab} onClick={onKeygrabChange ? () => onKeygrabChange(!automation.keygrab) : undefined} />
          </SettingRow>
          <div className="py-2 text-[10.5px] leading-relaxed text-white/40">
            Captures keyboard shortcuts globally so key presses are routed to the mapper instead of the focused app.
          </div>
          <SettingRow label="Mouse Mode">
            <Toggle on={automation.mouseMode} onClick={onMouseModeChange ? () => onMouseModeChange(!automation.mouseMode) : undefined} />
          </SettingRow>
          <div className="py-2 text-[10.5px] leading-relaxed text-white/40">
            When enabled, clicking a note tile or CC bar populates the Quick Bind form. When disabled, tile clicks are inactive to prevent accidental mapping changes.
          </div>
        </div>
      </section>

      {/* Runtime info */}
      <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
        <SectionHeader>Runtime</SectionHeader>
        <div className="divide-y divide-white/[0.06]">
          <SettingRow label="Runtime">
            <span className="rounded border border-cyan-300/20 bg-cyan-300/[0.07] px-2 py-px text-[11px] font-mono text-cyan-100/80">
              v2 runtime active
            </span>
          </SettingRow>
          <div className="py-2 text-[10.5px] leading-relaxed text-white/40">
            MIDI matching and command execution are handled by the v2 runtime.
          </div>
        </div>
      </section>
    </div>
  );
}
