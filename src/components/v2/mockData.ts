import type {
  AppStats,
  AutomationState,
  CcBar,
  CcControl,
  KeyboardNote,
  MidiMonitorEvent,
  NoteDotColor,
  V2BindingSummary,
  V2LayerSummary,
  V2ProfileSummary,
  V2RunSummary,
} from "./types";

export const automationState: AutomationState = {
  armed: true,
  matchingMode: "legacy",
  mouseMode: false,
  liveConsole: true,
  keygrab: true,
};

export const profiles: V2ProfileSummary[] = [
  {
    id: "profile-live",
    name: "Live Performance",
    description: "Stage rig · transport + scene cues",
    active: true,
    starred: true,
    layerCount: 4,
    bindingCount: 12,
  },
  {
    id: "profile-studio",
    name: "Studio Workflow",
    description: "Editor, browser, transport, and utility shortcuts",
    active: false,
    layerCount: 3,
    bindingCount: 18,
  },
  {
    id: "profile-streamdeck",
    name: "Stream Deck Control",
    description: "OBS scenes and audio bus toggles",
    active: false,
    layerCount: 2,
    bindingCount: 11,
  },
  {
    id: "profile-ableton",
    name: "Ableton Shorts",
    description: "Clip launch · scene quantize",
    active: false,
    layerCount: 2,
    bindingCount: 9,
  },
  {
    id: "profile-test",
    name: "Test Profile",
    description: "Scratch space",
    active: false,
    layerCount: 1,
    bindingCount: 3,
  },
];

export const layers: V2LayerSummary[] = [
  { id: "layer-default", name: "Default Layer", active: true, bindingCount: 4, color: "#00d4ff" },
  { id: "layer-transport", name: "Transport", active: false, bindingCount: 4, color: "#00bd7d" },
  { id: "layer-effects", name: "Effects", active: false, bindingCount: 2, color: "#b08bff" },
  { id: "layer-instruments", name: "Instruments", active: false, bindingCount: 2, color: "#ffcc66" },
];

export const bindings: V2BindingSummary[] = [
  {
    id: "bind-c3",
    kind: "note",
    triggerLabel: "C3 (60)",
    triggerCondition: "Vel 90-127",
    actionLabel: "osascript -e 'tell app \"Spotify\" to play'",
    command: "osascript",
    layer: "Default Layer",
    enabled: true,
    requireArmed: true,
    label: "Spotify Play",
    trigger: "Note C3 · velocity 90-127",
    action: "osascript -e ...",
  },
  {
    id: "bind-cc21",
    kind: "cc",
    triggerLabel: "CC 21 (Knob 1)",
    triggerCondition: "0-127",
    actionLabel: "Volume Control (AppleScript)",
    command: "osascript",
    layer: "Default Layer",
    enabled: true,
    requireArmed: true,
    label: "Volume Control",
    trigger: "CC 21",
    action: "Volume Control",
  },
  {
    id: "bind-f2",
    kind: "note",
    triggerLabel: "F#2 (54)",
    triggerCondition: "Vel 0-127",
    actionLabel: "Toggle Mute (Logic Pro)",
    command: "osascript",
    layer: "Transport",
    enabled: true,
    requireArmed: true,
    label: "Toggle Mute",
    trigger: "Note F#2",
    action: "Toggle Mute",
  },
  {
    id: "bind-cc7",
    kind: "cc",
    triggerLabel: "CC 7 (Fader 1)",
    triggerCondition: "≥ 64",
    actionLabel: "osascript -e 'tell app \"Logic Pro\" to toggle play'",
    command: "osascript",
    layer: "Transport",
    enabled: true,
    requireArmed: true,
    label: "Logic Pro Play",
    trigger: "CC 7 · value ≥ 64",
    action: "Logic Pro Play",
  },
];

export const runs: V2RunSummary[] = [
  {
    id: "run-1",
    kind: "cc",
    triggerLabel: "CC 21 (Knob 1)",
    triggerCondition: "",
    actionLabel: "Volume Control (AppleScript)",
    status: "success",
    relativeTime: "2s ago",
    durationMs: 41,
    action: "Volume Control",
    time: "12:42:18",
  },
  {
    id: "run-2",
    kind: "note",
    triggerLabel: "C3 (60)",
    triggerCondition: "Vel 100",
    actionLabel: "Spotify Play",
    status: "success",
    relativeTime: "5s ago",
    durationMs: 17,
    action: "Spotify Play",
    time: "12:42:11",
  },
  {
    id: "run-3",
    kind: "note",
    triggerLabel: "F#2 (54)",
    triggerCondition: "Vel 64",
    actionLabel: "Toggle Mute (Logic Pro)",
    status: "success",
    relativeTime: "12s ago",
    durationMs: 24,
    action: "Toggle Mute",
    time: "12:42:04",
  },
  {
    id: "run-4",
    kind: "cc",
    triggerLabel: "CC 7 (Fader 1)",
    triggerCondition: "",
    actionLabel: "Logic Pro Play",
    status: "success",
    relativeTime: "18s ago",
    durationMs: 18,
    action: "Logic Pro Play",
    time: "12:41:58",
  },
  {
    id: "run-5",
    kind: "note",
    triggerLabel: "D#3 (63)",
    triggerCondition: "Vel 80",
    actionLabel: "Custom Script",
    status: "failed",
    statusDetail: "1",
    relativeTime: "25s ago",
    durationMs: 8,
    action: "Custom Script",
    time: "12:41:51",
  },
];

export const monitorEvents: MidiMonitorEvent[] = [
  { id: "evt-1", port: "Oxygen Pro 49", type: "note_on", channel: 1, value: "C3 (60) · vel 100", matched: true },
  { id: "evt-2", port: "Oxygen Pro 49", type: "control_change", channel: 1, value: "CC 21 · 63", matched: true },
  { id: "evt-3", port: "Launch Control", type: "control_change", channel: 3, value: "CC 21 · 12", matched: false },
];

const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

// Note dot map: index → array of dot colors (representing bound bindings/layers)
const NOTE_DOTS: Record<number, NoteDotColor[]> = {
  60: ["cyan", "amber"], // C3 (selected target)
  48: ["cyan"],
  49: ["amber"],
  50: ["cyan"],
  51: ["orange"],
  54: ["emerald"],
  62: ["cyan"],
  63: ["amber"],
  65: ["purple"],
  67: ["cyan", "amber"],
  72: ["cyan"],
  74: ["purple"],
  79: ["emerald"],
  84: ["cyan"],
  91: ["amber"],
  97: ["purple"],
  102: ["cyan"],
  111: ["amber"],
};

// 72 notes (C3=48 through B8=119). Exactly 6 complete octaves in a 12-col grid.
export const keyboardNotes: KeyboardNote[] = Array.from({ length: 72 }, (_, index) => {
  const note = 48 + index;
  const name = NOTE_NAMES[note % 12];
  const octave = Math.floor(note / 12) - 1;
  const dots = NOTE_DOTS[note];
  return {
    note,
    label: `${name}${octave}`,
    bound: Boolean(dots),
    active: note === 60,
    pressed: note === 60,
    velocity: note === 60 ? 100 : undefined,
    dots,
  };
});

export const ccControls: CcControl[] = [
  { id: "cc-filter", label: "Filter", controller: 74, value: 63, threshold: [32, 96] },
  { id: "cc-volume", label: "Volume", controller: 7, value: 92, threshold: [1, 127] },
  { id: "cc-pan", label: "Pan", controller: 10, value: 54, threshold: [20, 108] },
  { id: "cc-send", label: "Send", controller: 91, value: 18, threshold: [64, 127] },
];

// 16 narrow CC bars (CC 0 through CC 15) — small dashboard visualization.
export const ccBars: CcBar[] = [
  { index: 0, value: 64 },
  { index: 1, value: 0 },
  { index: 2, value: 127, color: "emerald" },
  { index: 3, value: 32 },
  { index: 4, value: 0 },
  { index: 5, value: 96, color: "orange" },
  { index: 6, value: 0 },
  { index: 7, value: 64, color: "purple" },
  { index: 8, value: 0 },
  { index: 9, value: 0 },
  { index: 10, value: 10, color: "red" },
  { index: 11, value: 0 },
  { index: 12, value: 0 },
  { index: 13, value: 0 },
  { index: 14, value: 0 },
  { index: 15, value: 0 },
];

export const appStats: AppStats = {
  midiInput: "Midi Through:Midi Through Port-0",
  lastEvent: "Note On  Ch 1  C3 (60)  Vel 100",
  profiles: 5,
  layers: 4,
  bindings: 12,
  actions: 12,
};
