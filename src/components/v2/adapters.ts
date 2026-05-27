import type {
  AppStats,
  AutomationState,
  BindingKind,
  RunStatus,
  SessionStatus,
  V2BindingSummary,
  V2ActionStep,
  V2ExecutionSession,
  V2LayerSummary,
  V2Macro,
  V2ProfileSummary,
  V2RunSummary,
} from "./types";
import type {
  BackendAutomationSettings,
  BackendBinding,
  BackendDevice,
  BackendLayer,
  BackendMacro,
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

/** Formats a 0-based MIDI channel to a 1-based display label: "Ch 1" */
export function channelLabel(channel: number | null | undefined): string {
  return `Ch ${(channel ?? 0) + 1}`;
}

/**
 * Produces a full trigger label including channel prefix.
 * Use this for standalone string contexts (run history, console, actions panel)
 * where channel is not rendered separately.
 * Example: "Ch 1 · C3 (48)"
 */
export function formatTriggerWithChannel(
  channel: number | null | undefined,
  label: string,
): string {
  return `${channelLabel(channel)} · ${label}`;
}

function mapActionStep(action: NonNullable<BackendBinding["actions"]>[number], fallbackIndex: number): V2ActionStep {
  const type = action.type ?? "command";
  const durationMs = action.duration_ms ?? undefined;
  const command = action.command?.trim() || "";
  const title = (action as Record<string, unknown>)["title"] as string | undefined;
  const message = (action as Record<string, unknown>)["message"] as string | undefined;
  const urgency = (action as Record<string, unknown>)["urgency"] as string | undefined;

  function autoLabel(): string {
    if (action.label?.trim()) return action.label.trim();
    if (type === "delay") return `Wait ${durationMs ?? 0}ms`;
    if (type === "notification") return `Notify: ${title?.trim() || "Notification"}`;
    if (type === "open_url") return `Open URL: ${command}`;
    if (type === "open_app") return `Open App: ${command.split(" ")[0] || "app"}`;
    if (type === "hotkey") return `Hotkey: ${command}`;
    return command || "Command";
  }

  return {
    bindingActionId: String(action.binding_action_id ?? action.action_id ?? action.id ?? fallbackIndex),
    bindingId: String(action.binding_id ?? ""),
    actionId: String(action.action_id ?? action.id ?? fallbackIndex),
    executionOrder: action.execution_order ?? fallbackIndex,
    enabled: asBool(action.enabled ?? 1),
    type,
    label: autoLabel(),
    command: command || undefined,
    durationMs,
    workingDirectory: action.working_directory?.trim() || undefined,
    executionMode: action.execution_mode ?? undefined,
    timeoutMs: action.timeout_ms ?? undefined,
    title: title?.trim() || undefined,
    message: message?.trim() || undefined,
    urgency: urgency?.trim() || undefined,
  };
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

    const actions = (binding.actions?.length
      ? binding.actions
      : binding.action
        ? [{ ...binding.action, action_id: binding.action.id, binding_id: binding.id, execution_order: 0, enabled: 1 }]
        : []
    ).map(mapActionStep);

    return {
      id: String(binding.id),
      kind,
      actionId:
        binding.action?.id == null && binding.action_id == null
          ? undefined
          : String(binding.action?.id ?? binding.action_id),
      triggerId: binding.trigger_id == null ? undefined : String(binding.trigger_id),
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
      workingDirectory: binding.action?.working_directory?.trim() || undefined,
      executionMode: binding.action?.execution_mode ?? undefined,
      timeoutMs: binding.action?.timeout_ms ?? undefined,
      layer: layerNames.get(String(binding.layer_id)) ?? "Layer",
      enabled: asBool(binding.enabled),
      requireArmed: asBool(binding.require_armed),
      cooldownMs: binding.cooldown_ms ?? undefined,
      notes: binding.notes ?? undefined,
      displayColor: binding.display_color?.trim() || undefined,
      displayLabel: binding.display_label?.trim() || undefined,
      icon: binding.display_icon?.trim() || undefined,
      actions,
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
      triggerLabel: trigger ? formatTriggerWithChannel(trigger.channel, triggerLabel(trigger)) : "Trigger",
      triggerCondition: condition,
      actionLabel: action,
      status: mapStatus(run.status),
      statusDetail: run.exit_code == null ? run.error_message || undefined : String(run.exit_code),
      relativeTime: relativeTime(run.started_at ?? run.created_at),
      durationMs: run.duration_ms ?? 0,
      stdoutPreview: run.stdout_preview?.trim() || undefined,
      stderrPreview: run.stderr_preview?.trim() || undefined,
      errorMessage: run.error_message?.trim() || undefined,
      startedAt: run.started_at ?? undefined,
      sessionId: run.session_id ?? undefined,
      action,
      time: run.started_at ? new Date(run.started_at).toLocaleTimeString() : undefined,
    };
  });
}

export function groupRunsIntoSessions(runs: V2RunSummary[]): V2ExecutionSession[] {
  const sessionMap = new Map<string, V2ExecutionSession>();
  const singletons: V2ExecutionSession[] = [];

  for (const run of runs) {
    if (!run.sessionId) {
      singletons.push({
        sessionId: `single-${run.id}`,
        triggerLabel: run.triggerLabel,
        triggerCondition: run.triggerCondition,
        startedAt: run.startedAt,
        totalDurationMs: run.durationMs,
        status: run.status,
        stepCount: 1,
        failureCount: run.status !== "success" ? 1 : 0,
        steps: [run],
      });
      continue;
    }

    const existing = sessionMap.get(run.sessionId);
    if (!existing) {
      sessionMap.set(run.sessionId, {
        sessionId: run.sessionId,
        triggerLabel: run.triggerLabel,
        triggerCondition: run.triggerCondition,
        startedAt: run.startedAt,
        totalDurationMs: run.durationMs,
        status: run.status as SessionStatus,
        stepCount: 1,
        failureCount: run.status !== "success" ? 1 : 0,
        steps: [run],
      });
    } else {
      existing.steps.push(run);
      existing.totalDurationMs += run.durationMs;
      existing.stepCount++;
      if (run.status !== "success") {
        existing.failureCount++;
        existing.status = "partial";
      }
      if (run.startedAt && existing.startedAt && run.startedAt < existing.startedAt) {
        existing.startedAt = run.startedAt;
        existing.triggerLabel = run.triggerLabel;
        existing.triggerCondition = run.triggerCondition;
      }
    }
  }

  return [...sessionMap.values(), ...singletons].sort((a, b) => {
    if (!a.startedAt) return 1;
    if (!b.startedAt) return -1;
    return b.startedAt.localeCompare(a.startedAt);
  });
}

export function mapMacros(rows: BackendMacro[]): V2Macro[] {
  return rows.map((macro) => ({
    id: String(macro.id),
    name: macro.name,
    description: macro.description?.trim() || "",
    stepCount: macro.step_count ?? 0,
    createdAt: macro.created_at ?? undefined,
  }));
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
  const actionCount = bindings.reduce((total, binding) => total + Math.max(1, binding.actions?.length ?? 0), 0);
  return {
    ...fallback,
    midiInput: connectedDevice?.port_name || connectedDevice?.name || fallback.midiInput,
    profiles: profiles.length,
    layers: layers.length,
    bindings: bindings.length,
    actions: actionCount,
  };
}
