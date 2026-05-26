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

export type NoteDotColor = "cyan" | "purple" | "amber" | "orange" | "red" | "emerald";

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
