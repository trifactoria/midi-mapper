import type {
  AppStats,
  AutomationState,
  BindingKind,
  RunStatus,
  V2BindingSummary,
  V2LayerSummary,
  V2ProfileSummary,
  V2RunSummary,
} from "./types";
import type {
  BackendAutomationSettings,
  BackendBinding,
  BackendDevice,
  BackendLayer,
  BackendMatchingSettings,
  BackendProfile,
  BackendRun,
  BackendTrigger,
} from "./api";

const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const LAYER_COLORS = ["#00d4ff", "#00bd7d", "#b08bff", "#ffcc66", "#ff7a66", "#6ee7b7"];

function asBool(value: boolean | number | null | undefined): boolean {
  return value === true || value === 1;
}

function noteLabel(note: number | null | undefined): string {
  if (typeof note !== "number") return "Note";
  const name = NOTE_NAMES[note % 12] ?? "Note";
  const octave = Math.floor(note / 12) - 1;
  return `${name}${octave} (${note})`;
}

function bindingKind(trigger?: BackendTrigger | null): BindingKind {
  return trigger?.event_type === "control_change" || typeof trigger?.controller === "number" ? "cc" : "note";
}

function triggerLabel(trigger?: BackendTrigger | null): string {
  if (!trigger) return "Trigger";
  if (bindingKind(trigger) === "cc") {
    return typeof trigger.controller === "number" ? `CC ${trigger.controller}` : "CC";
  }
  return noteLabel(trigger.note);
}

function triggerCondition(trigger?: BackendTrigger | null): string {
  if (!trigger) return "";
  if (bindingKind(trigger) === "cc") {
    if (typeof trigger.value_min === "number" && typeof trigger.value_max === "number") {
      return `${trigger.value_min}-${trigger.value_max}`;
    }
    if (typeof trigger.value_min === "number") return `>= ${trigger.value_min}`;
    if (typeof trigger.value_max === "number") return `<= ${trigger.value_max}`;
    return "0-127";
  }
  if (typeof trigger.velocity_min === "number" && typeof trigger.velocity_max === "number") {
    return `Vel ${trigger.velocity_min}-${trigger.velocity_max}`;
  }
  if (typeof trigger.velocity_min === "number") return `Vel >= ${trigger.velocity_min}`;
  if (typeof trigger.velocity_max === "number") return `Vel <= ${trigger.velocity_max}`;
  return "Vel 0-127";
}

function parseTriggerSnapshot(value: string | null | undefined): BackendTrigger | null {
  if (!value) return null;
  try {
    const parsed: unknown = JSON.parse(value);
    return parsed && typeof parsed === "object" ? (parsed as BackendTrigger) : null;
  } catch {
    return null;
  }
}

function relativeTime(value: string | null | undefined): string {
  if (!value) return "recently";
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return value;
  const seconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function mapStatus(status: string | null | undefined): RunStatus {
  if (status === "ok" || status === "success") return "success";
  if (status === "timeout") return "timeout";
  if (status === "failed") return "failed";
  return "error";
}

export function mapProfiles(rows: BackendProfile[]): V2ProfileSummary[] {
  return rows.map((profile) => ({
    id: String(profile.id),
    name: profile.name?.trim() || `Profile ${profile.id}`,
    description: profile.description?.trim() || "",
    active: asBool(profile.active),
    layerCount: profile.layer_count ?? 0,
    bindingCount: profile.binding_count ?? 0,
  }));
}

export function mapLayers(rows: BackendLayer[]): V2LayerSummary[] {
  return rows.map((layer, index) => ({
    id: String(layer.id),
    name: layer.name?.trim() || `Layer ${layer.id}`,
    active: asBool(layer.active),
    bindingCount: layer.binding_count ?? 0,
    color: layer.color || LAYER_COLORS[index % LAYER_COLORS.length],
  }));
}

export function mapBindings(rows: BackendBinding[], layers: V2LayerSummary[]): V2BindingSummary[] {
  const layerNames = new Map(layers.map((layer) => [layer.id, layer.name]));
  return rows.map((binding) => {
    const kind = bindingKind(binding.trigger);
    const label = binding.display_label?.trim() || binding.action?.label?.trim() || binding.action?.command?.trim() || "Command";
    const triggerText = triggerLabel(binding.trigger);
    const condition = triggerCondition(binding.trigger);

    return {
      id: String(binding.id),
      kind,
      actionId:
        binding.action?.id == null && binding.action_id == null
          ? undefined
          : String(binding.action?.id ?? binding.action_id),
      triggerLabel: triggerText,
      triggerCondition: condition,
      channel: binding.trigger?.channel ?? undefined,
      note: binding.trigger?.note ?? undefined,
      controller: binding.trigger?.controller ?? undefined,
      valueMin: binding.trigger?.value_min ?? undefined,
      valueMax: binding.trigger?.value_max ?? undefined,
      velocityMin: binding.trigger?.velocity_min ?? undefined,
      velocityMax: binding.trigger?.velocity_max ?? undefined,
      actionLabel: label,
      command: binding.action?.command?.trim() || "",
      layer: layerNames.get(String(binding.layer_id)) ?? "Layer",
      enabled: asBool(binding.enabled),
      requireArmed: asBool(binding.require_armed),
      label,
      trigger: condition ? `${triggerText} · ${condition}` : triggerText,
      action: label,
    };
  });
}

export function mapRuns(rows: BackendRun[]): V2RunSummary[] {
  return rows.map((run) => {
    const trigger = parseTriggerSnapshot(run.trigger_snapshot_json);
    const action = run.action_summary?.trim() || "Command";
    const condition = triggerCondition(trigger);

    return {
      id: String(run.id),
      kind: bindingKind(trigger),
      triggerLabel: triggerLabel(trigger),
      triggerCondition: condition,
      actionLabel: action,
      status: mapStatus(run.status),
      statusDetail: run.exit_code == null ? run.error_message || undefined : String(run.exit_code),
      relativeTime: relativeTime(run.started_at ?? run.created_at),
      durationMs: run.duration_ms ?? 0,
      action,
      time: run.started_at ? new Date(run.started_at).toLocaleTimeString() : undefined,
    };
  });
}

export function mapAutomation(
  automation: BackendAutomationSettings | null,
  matching: BackendMatchingSettings | null,
  fallback: AutomationState,
): AutomationState {
  const matchingMode = matching?.matching_mode;
  return {
    ...fallback,
    armed: automation?.armed == null ? fallback.armed : asBool(automation.armed),
    keygrab: automation?.legacy_keygrab == null ? fallback.keygrab : asBool(automation.legacy_keygrab),
    matchingMode:
      matchingMode === "legacy" || matchingMode === "v2" || matchingMode === "dual"
        ? matchingMode
        : fallback.matchingMode,
  };
}

export function mapStats(
  profiles: V2ProfileSummary[],
  layers: V2LayerSummary[],
  bindings: V2BindingSummary[],
  devices: BackendDevice[],
  fallback: AppStats,
): AppStats {
  const connectedDevice = devices.find((device) => asBool(device.connected)) ?? devices[0];
  return {
    ...fallback,
    midiInput: connectedDevice?.port_name || connectedDevice?.name || fallback.midiInput,
    profiles: profiles.length,
    layers: layers.length,
    bindings: bindings.length,
    actions: bindings.length,
  };
}
