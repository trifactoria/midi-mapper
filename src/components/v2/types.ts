export type AutomationState = {
  armed: boolean;
  matchingMode: "legacy" | "v2" | "dual";
  mouseMode: boolean;
  liveConsole: boolean;
  keygrab: boolean;
};

export type V2ProfileSummary = {
  id: string;
  name: string;
  description: string;
  active: boolean;
  starred?: boolean;
  layerCount: number;
  bindingCount: number;
};

export type V2LayerSummary = {
  id: string;
  name: string;
  active: boolean;
  bindingCount: number;
  color: string;
};

export type BindingKind = "note" | "cc";

export type V2BindingSummary = {
  id: string;
  kind: BindingKind;
  actionId?: string;
  triggerLabel: string;
  triggerCondition: string;
  channel?: number;
  note?: number;
  controller?: number;
  valueMin?: number;
  valueMax?: number;
  velocityMin?: number;
  velocityMax?: number;
  actionLabel: string;
  command: string;
  layer: string;
  enabled: boolean;
  requireArmed: boolean;
  displayColor?: string;
  /** Legacy fields kept for back-compat with other panels */
  label?: string;
  trigger?: string;
  action?: string;
};

export type RunStatus = "success" | "failed" | "error" | "timeout";

export type V2RunSummary = {
  id: string;
  kind: BindingKind;
  triggerLabel: string;
  triggerCondition: string;
  actionLabel: string;
  status: RunStatus;
  statusDetail?: string;
  relativeTime: string;
  durationMs: number;
  /** Legacy fields */
  action?: string;
  time?: string;
};

export type MidiMonitorEvent = {
  id: string;
  port: string;
  type: string;
  channel: number;
  value: string;
  matched: boolean;
};

export type NoteDotColor = "cyan" | "purple" | "amber" | "orange" | "red" | "emerald" | "violet" | "rose" | "blue" | "slate";

export type KeyboardNote = {
  note: number;
  label: string;
  bound?: boolean;
  active?: boolean;
  pressed?: boolean;
  velocity?: number;
  dots?: NoteDotColor[];
};

export type CcControl = {
  id: string;
  label: string;
  controller: number;
  value: number;
  threshold: [number, number];
};

export type CcBar = {
  index: number;
  value: number;
  color?: "cyan" | "emerald" | "amber" | "orange" | "purple" | "red";
};

export type AppStats = {
  midiInput: string;
  lastEvent: string;
  profiles: number;
  layers: number;
  bindings: number;
  actions: number;
};

export type V2MidiEventPayload = {
  ts?: number;
  port_name?: string;
  source_port_name?: string;
  selected_input_port?: string | null;
  device_id?: number | string | null;
  type?: string;
  channel?: number | null;
  effective_channel?: number | null;
  note?: number | null;
  velocity?: number | null;
  cc?: number | null;
  value?: number | null;
  matched_binding_id?: number | string | null;
  matched_layer_id?: number | string | null;
  matched_profile_id?: number | string | null;
  action_execution?: {
    ok?: boolean;
    run_id?: number | string;
    error?: string;
    stdout?: string;
    stdout_preview?: string;
    stderr?: string;
    stderr_preview?: string;
  } | null;
  execution_status?: string | null;
  binding_match?: unknown;
  v2_binding_match?: unknown;
};
