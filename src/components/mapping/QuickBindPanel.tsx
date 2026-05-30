import { useEffect, useMemo, useRef, useState } from "react";
import { IconPicker } from "../IconPicker";
import { ToggleTrack } from "../ToggleSwitch";
import type { BackendActionPreviewPayload, BackendActionRunResult, BackendBindingCreatePayload } from "../v2/api";
import type { V2BindingSummary, V2MidiEventPayload } from "../v2/types";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-200/80">
      {children}
    </h3>
  );
}

function FieldLabel({ children, optional }: { children: React.ReactNode; optional?: boolean }) {
  return (
    <span className="mb-0.5 block text-[10px] uppercase tracking-[0.12em] text-white/45">
      {children}
      {optional && <span className="text-white/25"> (optional)</span>}
    </span>
  );
}

function Toggle({ on, label, onClick }: { on: boolean; label: string; onClick?: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center justify-between gap-3"
      style={{ background: "transparent", border: "none", padding: 0, minHeight: 0 }}
    >
      <span className="text-[11.5px] text-white/80">{label}</span>
      <ToggleTrack on={on} />
    </button>
  );
}

export type TileCapture =
  | { type: "note"; value: number; key: number }
  | { type: "cc"; value: number; key: number };

type ActionPreset = {
  id: string;
  label: string;
  command: string;
  args: string;
  hint?: string;
  execution_mode?: "argv" | "detached";
  action_type?: "command" | "notification" | "open_url" | "open_app" | "hotkey";
};

const PRESET_GROUPS: { group: string; items: ActionPreset[] }[] = [
  {
    group: "",
    items: [
      { id: "custom", label: "Custom Command", command: "echo", args: "hello" },
    ],
  },
  {
    group: "Desktop",
    items: [
      { id: "notify", label: "Desktop Notification", command: "Recording starting", args: "Scene is live", hint: "Uses notify-send — edit title and body", action_type: "notification" },
      { id: "open_url_native", label: "Open URL", command: "https://example.com", args: "", hint: "Requires xdg-open", action_type: "open_url" },
      { id: "open_app_native", label: "Open App", command: "firefox", args: "", hint: "Edit with your app name", action_type: "open_app" },
      { id: "hotkey_native", label: "Hotkey / Shortcut", command: "", args: "", hint: "Hotkeys are sent with xdotool and depend on your desktop shortcuts. Test carefully.", action_type: "hotkey" },
    ],
  },
  {
    group: "Open (command)",
    items: [
      { id: "open_url", label: "Open URL (cmd)", command: "xdg-open", args: "https://example.com", hint: "Requires xdg-open", execution_mode: "detached" },
      { id: "open_app", label: "Open App (cmd)", command: "firefox", args: "", hint: "Edit command to your app binary name", execution_mode: "detached" },
    ],
  },
  {
    group: "Media",
    items: [
      { id: "media_play_pause", label: "Media Play/Pause", command: "playerctl", args: "play-pause", hint: "Requires playerctl" },
      { id: "media_next", label: "Media Next", command: "playerctl", args: "next", hint: "Requires playerctl" },
      { id: "media_prev", label: "Media Previous", command: "playerctl", args: "previous", hint: "Requires playerctl" },
    ],
  },
  {
    group: "OBS",
    items: [
      { id: "obs_scene", label: "OBS Scene Switch", command: "obs-cmd", args: 'scene switch "Scene 1"', hint: "Requires obs-cmd  (pip install obs-cmd)" },
      { id: "obs_record_start", label: "OBS Start Recording", command: "obs-cmd", args: "recording start", hint: "Requires obs-cmd  (pip install obs-cmd)" },
      { id: "obs_record_stop", label: "OBS Stop Recording", command: "obs-cmd", args: "recording stop", hint: "Requires obs-cmd  (pip install obs-cmd)" },
    ],
  },
];

const ALL_PRESETS = PRESET_GROUPS.flatMap((g) => g.items);

const BINDING_COLORS = [
  { id: "cyan",    hex: "#22d3ee", label: "Cyan" },
  { id: "emerald", hex: "#34d399", label: "Emerald" },
  { id: "violet",  hex: "#a78bfa", label: "Violet" },
  { id: "amber",   hex: "#fbbf24", label: "Amber" },
  { id: "rose",    hex: "#fb7185", label: "Rose" },
  { id: "blue",    hex: "#60a5fa", label: "Blue" },
  { id: "slate",   hex: "#94a3b8", label: "Slate" },
] as const;

function bindingColorHex(color: string | undefined): string {
  if (color?.startsWith("#")) return color;
  return BINDING_COLORS.find((c) => c.id === color)?.hex ?? "#22d3ee";
}

type Props = {
  selectedBinding?: V2BindingSummary | null;
  canMutateBindings: boolean;
  onCreateBinding: (payload: BackendBindingCreatePayload) => Promise<V2BindingSummary>;
  onTestActionPreview: (payload: BackendActionPreviewPayload) => Promise<BackendActionRunResult>;
  onBindingCreated?: (binding: V2BindingSummary) => void;
  lastMidiEvent?: V2MidiEventPayload | null;
  tileCapture?: TileCapture | null;
};

const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
function noteName(note: number): string {
  const name = NOTE_NAMES[note % 12] ?? "Note";
  const octave = Math.floor(note / 12) - 1;
  return `${name}${octave}`;
}

function numberFromText(value: string): number | undefined {
  const match = value.match(/\d+/);
  if (!match) return undefined;
  const parsed = Number(match[0]);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function boundedMidiValue(value: string): number | undefined {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return undefined;
  return Math.max(0, Math.min(127, Math.round(parsed)));
}

function validateCreatePayload(
  eventType: "note" | "cc",
  channel: string,
  note: string,
  controller: string,
  velocityMin: string,
  velocityMax: string,
  valueMin: string,
  valueMax: string,
  commandLine: string,
): string | null {
  if (!commandLine.trim()) return "Command is required";
  const ch = Number(channel);
  if (!Number.isFinite(ch) || ch < 1 || ch > 16) return "Channel must be 1–16";
  if (eventType === "note") {
    const n = Number(note);
    if (!Number.isFinite(n) || n < 0 || n > 127) return "Note must be 0–127";
    const vMin = Number(velocityMin);
    const vMax = Number(velocityMax);
    if (!Number.isFinite(vMin) || vMin < 0 || vMin > 127) return "Velocity min must be 0–127";
    if (!Number.isFinite(vMax) || vMax < 0 || vMax > 127) return "Velocity max must be 0–127";
    if (vMin > vMax) return "Velocity min cannot exceed max";
  } else {
    const ctrl = Number(controller);
    if (!Number.isFinite(ctrl) || ctrl < 0 || ctrl > 127) return "Controller must be 0–127";
    const vMin = Number(valueMin);
    const vMax = Number(valueMax);
    if (!Number.isFinite(vMin) || vMin < 0 || vMin > 127) return "Value min must be 0–127";
    if (!Number.isFinite(vMax) || vMax < 0 || vMax > 127) return "Value max must be 0–127";
    if (vMin > vMax) return "Value min cannot exceed max";
  }
  return null;
}

function resultText(result: BackendActionRunResult | null): string | null {
  if (!result) return null;
  if (result.would_execute === false) return `Preview: ${result.command ?? result.summary ?? ""}`;
  if (result.error) return `Error: ${result.error}`;
  if (result.stderr || result.stderr_preview) return `stderr: ${result.stderr ?? result.stderr_preview}`;
  if (result.stdout || result.stdout_preview) return `stdout: ${result.stdout ?? result.stdout_preview}`;
  if (result.ok && result.command) return result.preview ? `Test ran: ${result.command}` : `Action ran: ${result.command}`;
  if (result.ok !== undefined) return result.ok ? "Action test succeeded" : "Action test failed";
  return null;
}

function resultDetail(result: BackendActionRunResult | null): React.ReactNode {
  if (!result) return null;
  const stdout = result.stdout ?? result.stdout_preview;
  const stderr = result.stderr ?? result.stderr_preview;
  if (!stdout && !stderr && !result.error) return null;
  return (
    <div className="mt-1.5 space-y-1 rounded border border-white/8 bg-black/25 p-2 font-mono text-[10px] leading-snug text-white/55">
      {stdout && <pre className="max-h-20 overflow-auto whitespace-pre-wrap text-emerald-100/75">{stdout}</pre>}
      {stderr && <pre className="max-h-20 overflow-auto whitespace-pre-wrap text-amber-100/75">{stderr}</pre>}
      {result.error && <pre className="max-h-20 overflow-auto whitespace-pre-wrap text-rose-100/75">{result.error}</pre>}
    </div>
  );
}

export function QuickBindPanel({
  selectedBinding,
  canMutateBindings,
  onCreateBinding,
  onTestActionPreview,
  onBindingCreated,
  lastMidiEvent,
  tileCapture,
}: Props) {
  const [eventType, setEventType] = useState<"note" | "cc">("note");
  const [channel, setChannel] = useState("1");
  const [note, setNote] = useState("60");
  const [controller, setController] = useState("21");
  const [velocityMin, setVelocityMin] = useState("64");
  const [velocityMax, setVelocityMax] = useState("127");
  const [valueMin, setValueMin] = useState("0");
  const [valueMax, setValueMax] = useState("127");
  const [command, setCommand] = useState("echo");
  const [args, setArgs] = useState("hello");
  const [executionMode, setExecutionMode] = useState<"argv" | "detached">("argv");
  const [workingDirectory, setWorkingDirectory] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [requireArmed, setRequireArmed] = useState(true);
  const [cooldownMs, setCooldownMs] = useState("250");
  const [debounceMs, setDebounceMs] = useState("20");
  const [notes, setNotes] = useState("");
  const [presetId, setPresetId] = useState("custom");
  const [displayColor, setDisplayColor] = useState<string>("cyan");
  const [displayIcon, setDisplayIcon] = useState("");
  const [colorOpen, setColorOpen] = useState(false);
  const colorPickerRef = useRef<HTMLDivElement>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<BackendActionRunResult | null>(null);
  const [captureMode, setCaptureMode] = useState<"idle" | "waiting">("idle");
  const [captureHint, setCaptureHint] = useState<string | null>(null);
  // stores the lastMidiEvent reference at arm time so we skip pre-existing events
  const captureArmedEventRef = useRef<V2MidiEventPayload | null | undefined>(undefined);

  useEffect(() => {
    if (!selectedBinding) return;
    setEventType(selectedBinding.kind);
    setChannel(String((selectedBinding.channel ?? 0) + 1));
    if (selectedBinding.kind === "cc") {
      setController(String(selectedBinding.controller ?? numberFromText(selectedBinding.triggerLabel) ?? 21));
      setValueMin(String(selectedBinding.valueMin ?? 0));
      setValueMax(String(selectedBinding.valueMax ?? 127));
    } else {
      setNote(String(selectedBinding.note ?? numberFromText(selectedBinding.triggerLabel) ?? 60));
      setVelocityMin(String(selectedBinding.velocityMin ?? 0));
      setVelocityMax(String(selectedBinding.velocityMax ?? 127));
    }
    setCommand(selectedBinding.command || selectedBinding.actionLabel || "echo");
    setArgs("");
    setExecutionMode(selectedBinding.executionMode === "detached" ? "detached" : "argv");
    setEnabled(selectedBinding.enabled);
    setRequireArmed(selectedBinding.requireArmed);
    setDisplayColor(selectedBinding.displayColor ?? "cyan");
    setDisplayIcon(selectedBinding.icon ?? "");
    setPresetId("custom");
    setRunResult(null);
  }, [selectedBinding]);

  // Populate fields from the next incoming MIDI event when capture is armed
  useEffect(() => {
    if (captureMode !== "waiting" || !lastMidiEvent) return;
    if (lastMidiEvent === captureArmedEventRef.current) return;

    const rawChannel = lastMidiEvent.effective_channel ?? lastMidiEvent.channel ?? 0;
    const ch = String((typeof rawChannel === "number" ? rawChannel : 0) + 1);

    if (lastMidiEvent.type === "note_on" && typeof lastMidiEvent.note === "number") {
      setEventType("note");
      setChannel(ch);
      setNote(String(lastMidiEvent.note));
      setVelocityMin("1");
      setVelocityMax("127");
      setCaptureHint(`Captured ${noteName(lastMidiEvent.note)} (note ${lastMidiEvent.note})`);
      setCaptureMode("idle");
    } else if (lastMidiEvent.type === "control_change" && typeof lastMidiEvent.cc === "number") {
      setEventType("cc");
      setChannel(ch);
      setController(String(lastMidiEvent.cc));
      setValueMin("0");
      setValueMax("127");
      setCaptureHint(`Captured CC ${lastMidiEvent.cc}`);
      setCaptureMode("idle");
    }
  }, [lastMidiEvent, captureMode]);

  // Escape key cancels capture
  useEffect(() => {
    if (captureMode !== "waiting") return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setCaptureMode("idle");
        setCaptureHint(null);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [captureMode]);

  // Note tile / CC bar click → populate fields
  useEffect(() => {
    if (!tileCapture) return;
    setCaptureMode("idle");
    setCaptureHint(null);
    if (tileCapture.type === "note") {
      setEventType("note");
      setNote(String(tileCapture.value));
    } else {
      setEventType("cc");
      setController(String(tileCapture.value));
    }
  }, [tileCapture]);

  // Close color picker on outside click
  useEffect(() => {
    if (!colorOpen) return;
    const handler = (e: MouseEvent) => {
      if (!colorPickerRef.current?.contains(e.target as Node)) setColorOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [colorOpen]);

  function toggleCapture() {
    if (captureMode === "waiting") {
      setCaptureMode("idle");
      setCaptureHint(null);
    } else {
      captureArmedEventRef.current = lastMidiEvent;
      setCaptureMode("waiting");
      setCaptureHint(null);
    }
  }

  function applyPreset(id: string) {
    setPresetId(id);
    if (id === "custom") return; // keep current command/args when reverting to custom
    const preset = ALL_PRESETS.find((p) => p.id === id);
    if (!preset) return;
    setCommand(preset.command);
    setArgs(preset.args);
    setExecutionMode(preset.execution_mode ?? "argv");
  }

  const activePreset = ALL_PRESETS.find((p) => p.id === presetId);
  const nativeType = activePreset?.action_type;
  const commandLine = useMemo(() => [command.trim(), args.trim()].filter(Boolean).join(" "), [args, command]);
  const effectiveLabel = presetId !== "custom" && activePreset
    ? activePreset.label
    : (command.trim() || commandLine);

  // Type-aware field metadata
  const commandFieldLabel = nativeType === "notification" ? "Title"
    : nativeType === "open_url" ? "URL"
    : nativeType === "hotkey" ? "Shortcut"
    : "Command";
  const commandFieldPlaceholder = nativeType === "hotkey" ? "ctrl+a, alt+f2, media keys, etc."
    : nativeType === "open_url" ? "https://example.com"
    : nativeType === "notification" ? "Notification title"
    : "";
  const argsFieldLabel = nativeType === "notification" ? "Message (body)" : "Arguments";
  const showArgsField = nativeType !== "open_url" && nativeType !== "hotkey";
  const showWorkingDirField = !nativeType || nativeType === "open_app";

  async function createBinding() {
    setRunResult(null);
    if (!canMutateBindings) {
      setMessage("No active layer — create or select a layer first");
      return;
    }
    if (!command.trim()) {
      setMessage(`${commandFieldLabel} is required`);
      return;
    }
    const validationError = validateCreatePayload(
      eventType, channel, note, controller, velocityMin, velocityMax, valueMin, valueMax,
      nativeType ? command.trim() : commandLine,
    );
    if (validationError) {
      setMessage(validationError);
      return;
    }

    // channel is stored 1-based in state for display; backend/matcher use 0-based MIDI channel
    const midiChannel = Number(channel) - 1;
    const trigger =
      eventType === "cc"
        ? {
            event_type: "control_change" as const,
            channel: midiChannel,
            controller: boundedMidiValue(controller),
            value_min: boundedMidiValue(valueMin),
            value_max: boundedMidiValue(valueMax),
          }
        : {
            event_type: "note_on" as const,
            channel: midiChannel,
            note: boundedMidiValue(note),
            velocity_min: boundedMidiValue(velocityMin),
            velocity_max: boundedMidiValue(velocityMax),
          };

    try {
      const nativeType = activePreset?.action_type;
      const actionPayload = nativeType === "notification"
        ? { type: "notification" as const, label: effectiveLabel, title: command.trim(), message: args.trim() || undefined }
        : nativeType === "open_url"
        ? { type: "open_url" as const, label: effectiveLabel, command: command.trim() }
        : nativeType === "open_app"
        ? { type: "open_app" as const, label: effectiveLabel, command: commandLine }
        : nativeType === "hotkey"
        ? { type: "hotkey" as const, label: effectiveLabel, command: command.trim() }
        : {
            type: "command" as const,
            label: effectiveLabel,
            command: commandLine,
            working_directory: workingDirectory.trim() || undefined,
            execution_mode: executionMode,
          };
      const created = await onCreateBinding({
        trigger,
        action: actionPayload,
        enabled: enabled ? 1 : 0,
        require_armed: requireArmed ? 1 : 0,
        cooldown_ms: Number(cooldownMs) || 200,
        notes,
        display_label: effectiveLabel,
        display_color: displayColor,
        display_icon: displayIcon || undefined,
      });
      setMessage("Binding created");
      onBindingCreated?.(created);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Create binding failed");
    }
  }

  function actionPreviewPayload(): BackendActionPreviewPayload | null {
    setMessage(null);
    setRunResult(null);
    if (!command.trim()) {
      setRunResult({ ok: false, error: `${commandFieldLabel} is required` });
      return null;
    }
    if (nativeType === "notification") {
      return { type: "notification", label: effectiveLabel, title: command.trim(), message: args.trim() || undefined };
    }
    if (nativeType === "open_url") {
      return { type: "open_url", label: effectiveLabel, command: command.trim() };
    }
    if (nativeType === "open_app") {
      return { type: "open_app", label: effectiveLabel, command: commandLine };
    }
    if (nativeType === "hotkey") {
      return { type: "hotkey", label: effectiveLabel, command: command.trim() };
    }
    return {
      type: "command",
      label: effectiveLabel,
      command: commandLine,
      working_directory: workingDirectory.trim() || undefined,
      execution_mode: executionMode,
    };
  }

  function _previewSummary(payload: BackendActionPreviewPayload): string {
    if (payload.type === "notification") return `notify-send "${payload.title || ""}" "${payload.message || ""}"`;
    if (payload.type === "open_url") return `xdg-open ${payload.command || ""}`;
    if (payload.type === "open_app") return payload.command || "";
    if (payload.type === "hotkey") return `xdotool key ${payload.command || ""}`;
    return payload.command || "";
  }

  function previewCommand() {
    const payload = actionPreviewPayload();
    if (!payload) return;
    setRunResult({
      ok: true,
      command: payload.type === "command" ? payload.command : undefined,
      label: payload.label,
      summary: _previewSummary(payload),
      would_execute: false,
    });
  }

  async function testAction() {
    const payload = actionPreviewPayload();
    if (!payload) return;
    try {
      const result = await onTestActionPreview(payload);
      setRunResult(result);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Test action failed");
    }
  }

  return (
    <div className="space-y-2">
      {/* Quick Bind */}
      <section className="rounded-md border border-white/8 bg-white/[0.014] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.018),inset_0_0_24px_rgba(0,0,0,0.18)]">
        <div className="mb-1.5 flex items-center justify-between">
          <SectionLabel>Quick Bind</SectionLabel>
          {/* Color + icon selectors */}
          <div className="flex items-center gap-1.5">
            <IconPicker value={displayIcon} onChange={setDisplayIcon} color={bindingColorHex(displayColor)} />
            <div ref={colorPickerRef} className="relative">
            <button
              type="button"
              onClick={() => setColorOpen((o) => !o)}
              className="flex items-center gap-1 rounded border border-white/10 bg-white/[0.04] !px-1.5 !py-[3px] text-white/60 hover:bg-white/[0.07]"
              aria-label="Binding color"
            >
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: bindingColorHex(displayColor) }}
              />
              <svg viewBox="0 0 10 6" className="h-1.5 w-1.5" fill="currentColor">
                <path d="M0 0l5 6 5-6H0z" />
              </svg>
            </button>
            {colorOpen && (
              <div className="absolute right-0 top-full z-20 mt-1 flex gap-1 rounded-md border border-white/12 bg-zinc-900 p-1.5 shadow-xl">
                {BINDING_COLORS.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    title={c.label}
                    onClick={() => { setDisplayColor(c.id); setColorOpen(false); }}
                    className={[
                      "h-5 w-5 rounded-full transition",
                      displayColor === c.id ? "ring-2 ring-white/60 ring-offset-1 ring-offset-zinc-900" : "opacity-70 hover:opacity-100",
                    ].join(" ")}
                    style={{ backgroundColor: c.hex }}
                  />
                ))}
              </div>
            )}
            </div>
          </div>
        </div>

        {!canMutateBindings && (
          <p className="mb-2 rounded border border-white/8 bg-white/[0.025] px-2 py-1.5 text-[11px] text-white/45">
            No active layer — create or select a layer to start mapping
          </p>
        )}

        <div className="grid grid-cols-3 gap-1.5">
          <label className="block">
            <FieldLabel>Event Type</FieldLabel>
            <select className="w-full !text-[11.5px]" value={eventType} onChange={(event) => setEventType(event.target.value as "note" | "cc")}>
              <option value="note">Note</option>
              <option value="cc">CC</option>
            </select>
          </label>
          <label className="block">
            <FieldLabel>Channel</FieldLabel>
            <select className="w-full !text-[11.5px]" value={channel} onChange={(event) => setChannel(event.target.value)}>
              {Array.from({ length: 16 }, (_, i) => (
                <option key={i + 1}>{i + 1}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <FieldLabel>{eventType === "cc" ? "Controller" : "Note"}</FieldLabel>
            <input className="w-full font-mono !text-[11.5px]" value={eventType === "cc" ? controller : note} onChange={(event) => eventType === "cc" ? setController(event.target.value) : setNote(event.target.value)} />
          </label>
        </div>

        <div className="mt-2 grid grid-cols-[1fr_auto] items-end gap-1.5">
          <div className="grid grid-cols-2 gap-1.5">
            <label className="block">
              <FieldLabel>{eventType === "cc" ? "Value Min" : "Velocity Min"}</FieldLabel>
              <input className="w-full font-mono !text-[11.5px]" value={eventType === "cc" ? valueMin : velocityMin} onChange={(event) => eventType === "cc" ? setValueMin(event.target.value) : setVelocityMin(event.target.value)} />
            </label>
            <label className="block">
              <FieldLabel>{eventType === "cc" ? "Value Max" : "Velocity Max"}</FieldLabel>
              <input className="w-full font-mono !text-[11.5px]" value={eventType === "cc" ? valueMax : velocityMax} onChange={(event) => eventType === "cc" ? setValueMax(event.target.value) : setVelocityMax(event.target.value)} />
            </label>
          </div>
          <button
            type="button"
            onClick={toggleCapture}
            className={[
              "!h-7 shrink-0 rounded-md border !px-2.5 !text-[10.5px] uppercase tracking-[0.10em] font-semibold transition",
              captureMode === "waiting"
                ? "border-amber-300/40 bg-amber-300/[0.14] text-amber-200 hover:bg-amber-300/[0.20] animate-pulse"
                : "border-cyan-300/30 bg-cyan-300/[0.10] text-cyan-100 hover:bg-cyan-300/[0.16]",
            ].join(" ")}
          >
            {captureMode === "waiting" ? "Cancel" : "Capture Next"}
          </button>
        </div>
        {captureMode === "waiting" && (
          <p className="mt-1.5 text-[10.5px] text-amber-200/70">Waiting for MIDI input… (Esc to cancel)</p>
        )}
        {captureMode === "idle" && captureHint && (
          <p className="mt-1.5 text-[10.5px] text-emerald-300/80">{captureHint}</p>
        )}
      </section>

      {/* Action Preview */}
      <section className="rounded-md border border-white/8 bg-white/[0.014] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.018),inset_0_0_24px_rgba(0,0,0,0.18)]">
        <div className="mb-1.5">
          <SectionLabel>Action Preview</SectionLabel>
        </div>

        <div className="grid grid-cols-[1fr_2fr] gap-1.5">
          <label className="block">
            <FieldLabel>Preset</FieldLabel>
            <select
              className="w-full !text-[11.5px]"
              value={presetId}
              onChange={(event) => applyPreset(event.target.value)}
            >
              {PRESET_GROUPS.map(({ group, items }) =>
                group ? (
                  <optgroup key={group} label={group}>
                    {items.map((item) => (
                      <option key={item.id} value={item.id}>{item.label}</option>
                    ))}
                  </optgroup>
                ) : (
                  items.map((item) => (
                    <option key={item.id} value={item.id}>{item.label}</option>
                  ))
                )
              )}
            </select>
          </label>
          <label className="block">
            <FieldLabel>{commandFieldLabel}</FieldLabel>
            <input
              className="w-full font-mono !text-[11.5px]"
              value={command}
              placeholder={commandFieldPlaceholder}
              onChange={(event) => { setCommand(event.target.value); }}
            />
          </label>
        </div>

        {showArgsField && (
          <label className="mt-1.5 block">
            <FieldLabel optional>{argsFieldLabel}</FieldLabel>
            <input
              className="w-full font-mono !text-[11.5px]"
              value={args}
              onChange={(event) => setArgs(event.target.value)}
            />
          </label>
        )}
        {activePreset?.hint && (
          <p className="mt-0.5 text-[10px] text-amber-200/50">{activePreset.hint}</p>
        )}

        {showWorkingDirField && (
          <label className="mt-1.5 block">
            <FieldLabel optional>Working Directory</FieldLabel>
            <input className="w-full font-mono !text-[11.5px]" value={workingDirectory} onChange={(event) => setWorkingDirectory(event.target.value)} />
          </label>
        )}

        <div className="mt-2 flex gap-1.5">
          <button
            type="button"
            onClick={() => void testAction()}
            className="inline-flex !h-7 items-center gap-1.5 rounded-md border border-purple-300/30 bg-purple-300/[0.10] !px-2.5 !text-[10.5px] uppercase tracking-[0.10em] font-semibold text-purple-100 hover:bg-purple-300/[0.16]"
          >
            <span aria-hidden>▶</span> Test Action
          </button>
          <button
            type="button"
            onClick={previewCommand}
            className="inline-flex !h-7 items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.03] !px-2.5 !text-[10.5px] uppercase tracking-[0.10em] font-semibold text-white/75 hover:bg-white/[0.06]"
          >
            Preview Command
          </button>
        </div>
        {resultText(runResult) && <div className="mt-1.5 truncate font-mono text-[10.5px] text-white/55">{resultText(runResult)}</div>}
        {resultDetail(runResult)}
      </section>

      {/* Binding Options */}
      <section className="rounded-md border border-white/8 bg-white/[0.014] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.018),inset_0_0_24px_rgba(0,0,0,0.18)]">
        <div className="mb-1.5">
          <SectionLabel>Binding Options</SectionLabel>
        </div>

        <div className="space-y-1.5">
          <Toggle on={enabled} label="Active" onClick={() => setEnabled((value) => !value)} />
          <Toggle on={requireArmed} label="Require Armed" onClick={() => setRequireArmed((value) => !value)} />
        </div>

        <div className="mt-2 grid grid-cols-2 gap-1.5">
          <label className="block">
            <FieldLabel>Cooldown (ms)</FieldLabel>
            <input className="w-full font-mono !text-[11.5px]" value={cooldownMs} onChange={(event) => setCooldownMs(event.target.value)} />
          </label>
          <label className="block">
            <FieldLabel>Debounce (ms)</FieldLabel>
            <input className="w-full font-mono !text-[11.5px]" value={debounceMs} onChange={(event) => setDebounceMs(event.target.value)} />
          </label>
        </div>

        <label className="mt-2 block">
          <FieldLabel optional>Notes</FieldLabel>
          <textarea
            className="block w-full font-mono !text-[11.5px]"
            rows={2}
            placeholder="Optional notes about this binding..."
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
        </label>

        <button
          type="button"
          onClick={() => void createBinding()}
          className="btn-primary mt-2 w-full rounded-md !text-[11.5px] !py-1.5"
        >
          + Create Binding
        </button>
        {message && <div className="mt-1.5 truncate font-mono text-[10.5px] text-white/55">{message}</div>}
      </section>
    </div>
  );
}
