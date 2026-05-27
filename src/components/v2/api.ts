import { API_BASE } from "../useMidiApi";

export const WS_EVENTS_URL = `${API_BASE.replace(/^http/, "ws")}/ws/events`;

export type BackendProfile = {
  id: number | string;
  name?: string | null;
  description?: string | null;
  active?: boolean | number | null;
  layer_count?: number | null;
  binding_count?: number | null;
};

export type BackendProfileExport = {
  app?: string;
  export_version?: number;
  schema_version: number;
  kind: "midi-mapper-v2-profile" | string;
  profile: {
    name: string;
    description?: string;
  };
  layers: unknown[];
  bindings_v2: unknown[];
  triggers: unknown[];
  actions: unknown[];
};

export type BackendProfileImportResult = {
  ok: boolean;
  profile_id: number | string;
  profile: BackendProfile;
};

export type BackendLayer = {
  id: number | string;
  name?: string | null;
  active?: boolean | number | null;
  color?: string | null;
  binding_count?: number | null;
};

export type BackendTrigger = {
  event_type?: string | null;
  channel?: number | null;
  note?: number | null;
  controller?: number | null;
  value_min?: number | null;
  value_max?: number | null;
  velocity_min?: number | null;
  velocity_max?: number | null;
  port_name?: string | null;
};

export type BackendAction = {
  id?: number | string | null;
  action_id?: number | string | null;
  binding_action_id?: number | string | null;
  binding_id?: number | string | null;
  execution_order?: number | null;
  enabled?: boolean | number | null;
  type?: "command" | "delay" | string | null;
  label?: string | null;
  command?: string | null;
  duration_ms?: number | null;
  working_directory?: string | null;
  execution_mode?: string | null;
  timeout_ms?: number | null;
  notify_text?: string | null;
  notify_emoji?: string | null;
  title?: string | null;
  message?: string | null;
  urgency?: string | null;
};

export type BackendBinding = {
  id: number | string;
  profile_id?: number | string | null;
  layer_id?: number | string | null;
  trigger_id?: number | string | null;
  action_id?: number | string | null;
  enabled?: boolean | number | null;
  require_armed?: boolean | number | null;
  cooldown_ms?: number | null;
  notes?: string | null;
  display_label?: string | null;
  display_color?: string | null;
  display_icon?: string | null;
  trigger?: BackendTrigger | null;
  action?: BackendAction | null;
  actions?: BackendAction[] | null;
};

export type BackendBindingPatch = {
  enabled?: 0 | 1;
  require_armed?: 0 | 1;
  cooldown_ms?: number;
  notes?: string;
  display_label?: string;
  display_color?: string;
  display_icon?: string;
  trigger?: {
    event_type?: string;
    channel?: number;
    note?: number;
    controller?: number;
    value_min?: number;
    value_max?: number;
    velocity_min?: number;
    velocity_max?: number;
  };
  action?: {
    command?: string;
    label?: string;
    working_directory?: string;
    execution_mode?: string;
    timeout_ms?: number;
  };
};

export type BackendBindingCreatePayload = {
  trigger: {
    event_type: "note_on" | "control_change";
    channel?: number;
    note?: number;
    controller?: number;
    value_min?: number;
    value_max?: number;
    velocity_min?: number;
    velocity_max?: number;
  };
  action: {
    type: "command" | "notification" | "open_url" | "open_app" | "hotkey";
    label: string;
    command?: string;
    working_directory?: string;
    execution_mode?: "argv" | "detached";
    title?: string;
    message?: string;
    urgency?: string;
  };
  enabled: 0 | 1;
  require_armed: 0 | 1;
  cooldown_ms: number;
  notes: string;
  display_label: string;
  display_color?: string;
  display_icon?: string;
};

export type BackendActionPreviewPayload = {
  type: "command" | "notification" | "open_url" | "open_app" | "hotkey";
  label?: string;
  command?: string;
  working_directory?: string;
  execution_mode?: "argv" | "detached";
  timeout_ms?: number;
  title?: string;
  message?: string;
  urgency?: string;
};

export type BackendBindingActionCreatePayload = {
  type: "delay" | "command" | "notification" | "open_url" | "open_app" | "hotkey";
  label?: string;
  command?: string;
  duration_ms?: number;
  working_directory?: string;
  timeout_ms?: number;
  enabled?: 0 | 1;
  execution_mode?: "argv" | "detached";
  title?: string;
  message?: string;
  urgency?: string;
};

export type BackendBindingActionPatchPayload = {
  execution_order?: number;
  enabled?: 0 | 1;
  label?: string;
  command?: string;
  duration_ms?: number;
  working_directory?: string;
  execution_mode?: "argv" | "detached";
  timeout_ms?: number;
  title?: string;
  message?: string;
  urgency?: string;
};

export type BackendActionRunResult = {
  ok?: boolean;
  action_id?: number | string;
  command?: string;
  label?: string;
  preview?: boolean;
  summary?: string;
  stdout?: string;
  stdout_preview?: string;
  stderr?: string;
  stderr_preview?: string;
  error?: string;
  exit_code?: number | null;
  run_id?: number | string;
  would_execute?: boolean;
};

export type BackendRun = {
  id: number | string;
  trigger_snapshot_json?: string | null;
  action_summary?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at?: string | null;
  duration_ms?: number | null;
  status?: string | null;
  exit_code?: number | null;
  stdout_preview?: string | null;
  stderr_preview?: string | null;
  error_message?: string | null;
  session_id?: string | null;
};

export type BackendMacro = {
  id: number | string;
  name: string;
  description?: string | null;
  step_count?: number | null;
  actions_json?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type BackendBindingClonePayload = {
  target_note?: number | null;
  target_channel?: number | null;
  target_controller?: number | null;
  target_event_type?: string | null;
  target_layer_id?: number | null;
  enabled?: 0 | 1;
};

export type BackendAutomationSettings = {
  armed?: boolean | number | null;
  legacy_keygrab?: boolean | number | null;
};

export type BackendMatchingSettings = {
  matching_mode?: "legacy" | "v2" | "dual" | string | null;
};

export type BackendDevice = {
  id: number | string;
  name?: string | null;
  port_name?: string | null;
  connected?: boolean | number | null;
};

export type BackendPort = {
  id: number | string;
  name: string;
  online?: boolean;
};

export type BackendInputSettings = {
  selected_input_port?: string | null;
  available_input_ports?: string[];
  source?: string;
};

export type BackendMidiStatus = {
  available?: boolean | null;
  degraded?: boolean | null;
  message?: string | null;
  error?: string | null;
  input_ports?: string[] | null;
  output_ports?: string[] | null;
  selected_input_port?: string | null;
};

export type BackendHealth = {
  ok?: boolean;
  midi?: BackendMidiStatus | null;
};

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`PATCH ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    let detail: string | undefined;
    try {
      const parsed = await response.json() as { detail?: string };
      if (typeof parsed?.detail === "string") detail = parsed.detail;
    } catch { /* ignore */ }
    throw new Error(detail ?? `POST ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    cache: "no-store",
  });
  if (!response.ok) {
    let detail: string | undefined;
    try {
      const body = await response.json() as { detail?: string };
      if (typeof body?.detail === "string") detail = body.detail;
    } catch { /* ignore */ }
    throw new Error(detail ?? `DELETE ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const v2Api = {
  profiles: () => apiGet<BackendProfile[]>("/api/profiles"),
  exportProfile: (profileId: string) => apiGet<BackendProfileExport>(`/api/profiles/${profileId}/export`),
  importProfile: (payload: BackendProfileExport) =>
    apiPost<BackendProfileImportResult>("/api/profiles/import", { payload }),
  layers: (profileId: string) => apiGet<BackendLayer[]>(`/api/profiles/${profileId}/layers`),
  bindings: (layerId: string) => apiGet<BackendBinding[]>(`/api/layers/${layerId}/bindings`),
  runs: () => apiGet<BackendRun[]>("/api/runs"),
  automation: () => apiGet<BackendAutomationSettings>("/api/settings/automation"),
  updateAutomation: (armed: boolean) => apiPatch<BackendAutomationSettings>("/api/settings/automation", { armed }),
  matching: () => apiGet<BackendMatchingSettings>("/api/settings/matching"),
  updateMatching: (matchingMode: "legacy" | "v2" | "dual") =>
    apiPatch<BackendMatchingSettings & { ok?: boolean; error?: string }>("/api/settings/matching", {
      matching_mode: matchingMode,
    }),
  devices: () => apiGet<BackendDevice[]>("/api/devices"),
  ports: () => apiGet<BackendPort[]>("/api/ports"),
  inputSettings: () => apiGet<BackendInputSettings>("/api/settings/input"),
  updateInputSettings: (selectedInputPort: string | null) =>
    apiPatch<BackendInputSettings>("/api/settings/input", { selected_input_port: selectedInputPort }),
  health: () => apiGet<BackendHealth>("/api/health"),
  clearRuns: () => apiDelete<{ ok: boolean; deleted: number }>("/api/runs"),
  createProfile: (name: string) => apiPost<BackendProfile>("/api/profiles", { name }),
  updateProfile: (profileId: string, name: string) => apiPatch<BackendProfile>(`/api/profiles/${profileId}`, { name }),
  createLayer: (profileId: string, name: string) =>
    apiPost<BackendLayer>(`/api/profiles/${profileId}/layers`, { name }),
  updateLayer: (layerId: string, name: string) => apiPatch<BackendLayer>(`/api/layers/${layerId}`, { name }),
  activateProfile: (profileId: string) => apiPost<BackendProfile>(`/api/profiles/${profileId}/activate`),
  activateLayer: (layerId: string) => apiPost<BackendLayer>(`/api/layers/${layerId}/activate`),
  createBinding: (layerId: string, payload: BackendBindingCreatePayload) =>
    apiPost<BackendBinding>(`/api/layers/${layerId}/bindings`, payload),
  patchBinding: (bindingId: string, payload: BackendBindingPatch) =>
    apiPatch<BackendBinding>(`/api/bindings/${bindingId}`, payload),
  duplicateBinding: (bindingId: string) =>
    apiPost<BackendBinding>(`/api/bindings/${bindingId}/duplicate`),
  deleteBinding: (bindingId: string) => apiDelete<{ ok?: boolean }>(`/api/bindings/${bindingId}`),
  deleteProfile: (profileId: string) => apiDelete<{ ok: boolean; deleted_profile_id: number; activated_profile_id: number | null }>(`/api/profiles/${profileId}`),
  deleteLayer: (layerId: string) => apiDelete<{ ok: boolean; deleted_layer_id: number; activated_layer_id: number | null }>(`/api/layers/${layerId}`),
  setKeygrab: (enabled: boolean) => apiPost<{ ok: boolean; keygrab: boolean }>(`/api/keygrab/set?enabled=${String(enabled)}`),
  dryRunAction: (actionId: string) => apiPost<BackendActionRunResult>(`/api/actions/${actionId}/dry_run`),
  testAction: (actionId: string) => apiPost<BackendActionRunResult>(`/api/actions/${actionId}/test`),
  testActionPreview: (payload: BackendActionPreviewPayload) =>
    apiPost<BackendActionRunResult>("/api/actions/preview/test", payload),
  createBindingAction: (bindingId: string, payload: BackendBindingActionCreatePayload) =>
    apiPost<BackendAction>(`/api/bindings/${bindingId}/actions`, payload),
  updateBindingAction: (bindingId: string, bindingActionId: string, payload: BackendBindingActionPatchPayload) =>
    apiPatch<BackendAction>(`/api/bindings/${bindingId}/actions/${bindingActionId}`, payload),
  deleteBindingAction: (bindingId: string, bindingActionId: string) =>
    apiDelete<{ ok: boolean; deleted_binding_action_id: number | string; deleted_action_id?: number | string | null }>(
      `/api/bindings/${bindingId}/actions/${bindingActionId}`,
    ),
  reorderBindingActions: (bindingId: string, orderedIds: string[]) =>
    apiPost<{ ok: boolean; actions: BackendAction[] }>(
      `/api/bindings/${bindingId}/actions/reorder`,
      orderedIds.map((id) => Number(id)),
    ),
  reorderActionGroup: (orderedIds: string[]) =>
    apiPost<{ ok: boolean }>("/api/action-groups/reorder", orderedIds.map((id) => Number(id))),
  macros: () => apiGet<BackendMacro[]>("/api/macros"),
  createMacro: (bindingId: string, name: string, description?: string) =>
    apiPost<BackendMacro>("/api/macros", { binding_id: Number(bindingId), name, description: description ?? "" }),
  deleteMacro: (macroId: string) =>
    apiDelete<{ ok: boolean; deleted_macro_id: number }>(`/api/macros/${macroId}`),
  applyMacro: (macroId: string, bindingId: string, replaceExisting?: boolean) =>
    apiPost<{ ok: boolean; action_count: number; binding_id: number }>(
      `/api/macros/${macroId}/apply`,
      { binding_id: Number(bindingId), replace_existing: replaceExisting ?? false },
    ),
  cloneBinding: (bindingId: string, payload: BackendBindingClonePayload) =>
    apiPost<BackendBinding>(`/api/bindings/${bindingId}/clone`, payload),
};
