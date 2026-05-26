import { API_BASE } from "../useMidiApi";

export type BackendProfile = {
  id: number | string;
  name?: string | null;
  description?: string | null;
  active?: boolean | number | null;
  layer_count?: number | null;
  binding_count?: number | null;
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
  label?: string | null;
  command?: string | null;
};

export type BackendBinding = {
  id: number | string;
  action_id?: number | string | null;
  layer_id?: number | string | null;
  enabled?: boolean | number | null;
  require_armed?: boolean | number | null;
  display_label?: string | null;
  trigger?: BackendTrigger | null;
  action?: BackendAction | null;
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
    type: "command";
    label: string;
    command: string;
    execution_mode?: "argv";
  };
  enabled: 0 | 1;
  require_armed: 0 | 1;
  cooldown_ms: number;
  notes: string;
  display_label: string;
};

export type BackendActionRunResult = {
  ok?: boolean;
  action_id?: number | string;
  command?: string;
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
  created_at?: string | null;
  duration_ms?: number | null;
  status?: string | null;
  exit_code?: number | null;
  error_message?: string | null;
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

export type BackendMidiStatus = {
  available?: boolean | null;
  degraded?: boolean | null;
  message?: string | null;
  error?: string | null;
  input_ports?: string[] | null;
  output_ports?: string[] | null;
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
    throw new Error(`POST ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`DELETE ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const v2Api = {
  profiles: () => apiGet<BackendProfile[]>("/api/profiles"),
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
  health: () => apiGet<BackendHealth>("/api/health"),
  activateProfile: (profileId: string) => apiPost<BackendProfile>(`/api/profiles/${profileId}/activate`),
  activateLayer: (layerId: string) => apiPost<BackendLayer>(`/api/layers/${layerId}/activate`),
  createBinding: (layerId: string, payload: BackendBindingCreatePayload) =>
    apiPost<BackendBinding>(`/api/layers/${layerId}/bindings`, payload),
  deleteBinding: (bindingId: string) => apiDelete<{ ok?: boolean }>(`/api/bindings/${bindingId}`),
  dryRunAction: (actionId: string) => apiPost<BackendActionRunResult>(`/api/actions/${actionId}/dry_run`),
  testAction: (actionId: string) => apiPost<BackendActionRunResult>(`/api/actions/${actionId}/test`),
};
