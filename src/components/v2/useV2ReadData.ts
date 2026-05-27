"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  appStats as mockAppStats,
  automationState as mockAutomationState,
  bindings as mockBindings,
  keyboardNotes as mockKeyboardNotes,
  layers as mockLayers,
  monitorEvents as mockMonitorEvents,
  profiles as mockProfiles,
  runs as mockRuns,
} from "./mockData";
import type {
  AppStats,
  AutomationState,
  CcBar,
  KeyboardNote,
  MidiMonitorEvent,
  NoteDotColor,
  V2BindingSummary,
  V2LayerSummary,
  V2MidiEventPayload,
  V2ProfileSummary,
  V2RunSummary,
} from "./types";
import { mapAutomation, mapBindings, mapLayers, mapProfiles, mapRuns, mapStats } from "./adapters";
import {
  v2Api,
  type BackendActionPreviewPayload,
  type BackendActionRunResult,
  type BackendBindingCreatePayload,
  type BackendBindingPatch,
  type BackendDevice,
  type BackendPort,
  type BackendProfileExport,
  type BackendProfileImportResult,
  type BackendMidiStatus,
  WS_EVENTS_URL,
} from "./api";

type V2ReadData = {
  profiles: V2ProfileSummary[];
  layers: V2LayerSummary[];
  bindings: V2BindingSummary[];
  runs: V2RunSummary[];
  automation: AutomationState;
  appStats: AppStats;
  monitorEvents: MidiMonitorEvent[];
  keyboardNotes: KeyboardNote[];
  ccBars: CcBar[];
  liveMatchedBindingId: string | null;
  lastMidiEvent: V2MidiEventPayload | null;
  loading: boolean;
  error: string | null;
  dataSourceLabel: "Real backend data" | "Backend unavailable";
  midiStatus: BackendMidiStatus | null;
  inputPorts: BackendPort[];
  selectedInputPort: string | null;
  setAutomationArmed: (armed: boolean) => Promise<void>;
  setSelectedInputPort: (portName: string | null) => Promise<void>;
  clearRuns: () => Promise<void>;
  createProfile: () => Promise<string | null>;
  renameProfile: (profileId: string, name: string) => Promise<void>;
  activateProfile: (profileId: string) => Promise<void>;
  createLayer: () => Promise<string | null>;
  renameLayer: (layerId: string, name: string) => Promise<void>;
  activateLayer: (layerId: string) => Promise<void>;
  canMutateBindings: boolean;
  createBinding: (payload: BackendBindingCreatePayload) => Promise<V2BindingSummary>;
  editBinding: (bindingId: string, patch: BackendBindingPatch) => Promise<void>;
  toggleBindingEnabled: (bindingId: string) => Promise<void>;
  duplicateBinding: (bindingId: string) => Promise<V2BindingSummary | null>;
  deleteBinding: (bindingId: string) => Promise<void>;
  deleteProfile: (profileId: string) => Promise<void>;
  deleteLayer: (layerId: string) => Promise<void>;
  exportProfile: (profileId: string) => Promise<BackendProfileExport>;
  importProfile: (payload: BackendProfileExport) => Promise<BackendProfileImportResult>;
  clearMonitorEvents: () => void;
  setKeygrab: (enabled: boolean) => Promise<void>;
  setMouseMode: (mouseMode: boolean) => void;
  simulateNote: (note: number, velocity?: number, matched?: boolean, matchedBindingId?: string | null) => void;
  simulateCc: (controller: number, value: number, matched?: boolean, matchedBindingId?: string | null) => void;
  dryRunAction: (actionId: string) => Promise<BackendActionRunResult>;
  testAction: (actionId: string) => Promise<BackendActionRunResult>;
  testActionPreview: (payload: BackendActionPreviewPayload) => Promise<BackendActionRunResult>;
};

type ReadResult<T> = {
  value: T | null;
  fallback: boolean;
};

type DataSource = "backend" | "mock";

const DEFAULT_CC_BARS: CcBar[] = Array.from({ length: 16 }, (_, index) => ({ index, value: 0 }));
type LiveNoteState = Record<number, { active: boolean; pressed: boolean; velocity?: number; matched?: boolean }>;

async function readOrFallback<T>(read: () => Promise<T>, isEmpty: (value: T) => boolean): Promise<ReadResult<T>> {
  try {
    const value = await read();
    return isEmpty(value) ? { value: null, fallback: true } : { value, fallback: false };
  } catch {
    return { value: null, fallback: true };
  }
}

function ensureOneActive<T extends { active: boolean }>(items: T[]): T[] {
  if (items.length === 0 || items.some((item) => item.active)) return items;
  return items.map((item, index) => (index === 0 ? { ...item, active: true } : item));
}

// Backend v2 route params are numeric; mock IDs like "profile-live" must never reach those endpoints.
function numericBackendId(id: string): string | null {
  return /^\d+$/.test(id) ? id : null;
}

const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

function displayChannel(event: V2MidiEventPayload): number {
  const channel = event.effective_channel ?? event.channel ?? 0;
  return typeof channel === "number" ? channel + 1 : 1;
}

function noteLabel(note: number): string {
  const name = NOTE_NAMES[note % 12] ?? "Note";
  // Match the product copy currently used for C3=60.
  const octave = Math.floor(note / 12) - 2;
  return `${name}${octave} (${note})`;
}

function formattedEventType(type?: string): string {
  if (type === "note_on") return "Note On";
  if (type === "note_off") return "Note Off";
  if (type === "control_change") return "CC";
  return type ? type.replace(/_/g, " ") : "MIDI";
}

function formatMidiEvent(event: V2MidiEventPayload): string {
  const type = event.type;
  const channel = displayChannel(event);
  const note = typeof event.note === "number" ? event.note : null;
  const velocity = typeof event.velocity === "number" ? event.velocity : null;
  const cc = typeof event.cc === "number" ? event.cc : null;
  const value = typeof event.value === "number" ? event.value : null;

  if (type === "note_on" && velocity !== 0 && note !== null) {
    return `Note On Ch ${channel} ${noteLabel(note)} Vel ${velocity ?? 0}`;
  }
  if ((type === "note_off" || (type === "note_on" && velocity === 0)) && note !== null) {
    return `Note Off Ch ${channel} ${noteLabel(note)}`;
  }
  if (type === "control_change" && cc !== null) {
    return `CC ${cc} Ch ${channel} Value ${value ?? 0}`;
  }
  return `${formattedEventType(type)} Ch ${channel}`;
}

function monitorEventFromPayload(event: V2MidiEventPayload): MidiMonitorEvent {
  const sourcePort = event.source_port_name ?? event.port_name ?? event.selected_input_port ?? "Unknown MIDI input";
  const isCc = event.type === "control_change";
  const isNoteOff = event.type === "note_off" || (event.type === "note_on" && event.velocity === 0);
  const noteValue =
    typeof event.note === "number"
      ? `${noteLabel(event.note)}${isNoteOff ? "" : ` · vel ${event.velocity ?? 0}`}`
      : "Note";
  const ccValue = typeof event.cc === "number" ? `CC ${event.cc} · ${event.value ?? 0}` : "CC";

  return {
    id: `ws-${event.ts ?? Date.now()}-${event.type ?? "midi"}-${event.note ?? event.cc ?? ""}`,
    port: sourcePort,
    type: isCc ? "CC" : isNoteOff ? "Note Off" : formattedEventType(event.type),
    channel: displayChannel(event),
    value: isCc ? ccValue : noteValue,
    matched: Boolean(event.matched_binding_id ?? event.v2_binding_match ?? event.binding_match),
  };
}

function updateCcBars(current: CcBar[], cc: number, value: number, matched: boolean): CcBar[] {
  const boundedValue = Math.max(0, Math.min(127, value));
  const color: CcBar["color"] = matched ? "emerald" : "cyan";
  const existingIndex = current.findIndex((bar) => bar.index === cc);
  if (existingIndex >= 0) {
    return current.map((bar, index) => (index === existingIndex ? { ...bar, value: boundedValue, color } : bar));
  }

  const replacementIndex = current.findIndex((bar) => !bar.color);
  const next = [...current];
  next[replacementIndex >= 0 ? replacementIndex : next.length - 1] = { index: cc, value: boundedValue, color };
  return next;
}

const VALID_DOT_COLORS = new Set<string>(["cyan","purple","amber","orange","red","emerald","violet","rose","blue","slate"]);
function asDotColor(color: string | undefined): NoteDotColor {
  return (color && VALID_DOT_COLORS.has(color) ? color : "cyan") as NoteDotColor;
}

const DOT_COLOR_HEX: Record<NoteDotColor, string> = {
  cyan: "#22d3ee",
  purple: "#c084fc",
  amber: "#fbbf24",
  orange: "#fb923c",
  red: "#f87171",
  emerald: "#34d399",
  violet: "#a78bfa",
  rose: "#fb7185",
  blue: "#60a5fa",
  slate: "#94a3b8",
};

function displayColorHex(color: string | undefined): string {
  if (!color) return DOT_COLOR_HEX.cyan;
  if (color.startsWith("#")) return color;
  return DOT_COLOR_HEX[asDotColor(color)];
}

export function useV2ReadData(): V2ReadData {
  const [profiles, setProfiles] = useState(mockProfiles);
  const [layers, setLayers] = useState(mockLayers);
  const [bindings, setBindings] = useState(mockBindings);
  const [runs, setRuns] = useState(mockRuns);
  const [automation, setAutomation] = useState(mockAutomationState);
  const [devices, setDevices] = useState<BackendDevice[]>([]);
  const [inputPorts, setInputPorts] = useState<BackendPort[]>([]);
  const [selectedInputPort, setSelectedInputPortState] = useState<string | null>(null);
  const [midiStatus, setMidiStatus] = useState<BackendMidiStatus | null>(null);
  const [profileSource, setProfileSource] = useState<DataSource>("mock");
  const [layerSource, setLayerSource] = useState<DataSource>("mock");
  const [dataSourceLabel, setDataSourceLabel] = useState<V2ReadData["dataSourceLabel"]>("Backend unavailable");
  const [monitorEvents, setMonitorEvents] = useState<MidiMonitorEvent[]>([]);
  const [liveNotes, setLiveNotes] = useState<LiveNoteState>({});
  const [ccBars, setCcBars] = useState<CcBar[]>(DEFAULT_CC_BARS);
  const [liveSourcePort, setLiveSourcePort] = useState<string | null>(null);
  const [liveLastEvent, setLiveLastEvent] = useState<string | null>(null);
  const [liveMatchedBindingId, setLiveMatchedBindingId] = useState<string | null>(null);
  const [lastMidiEvent, setLastMidiEvent] = useState<V2MidiEventPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (options?: { quiet?: boolean; signal?: AbortSignal }) => {
    if (!options?.quiet) setLoading(true);
    setError(null);

    const [profileResult, runResult, automationResult, deviceResult, portResult, inputResult, healthResult] = await Promise.all([
      readOrFallback(v2Api.profiles, () => false),
      readOrFallback(v2Api.runs, () => false),
      readOrFallback(v2Api.automation, () => false),
      readOrFallback(v2Api.devices, () => false),
      readOrFallback(v2Api.ports, () => false),
      readOrFallback(v2Api.inputSettings, () => false),
      readOrFallback(v2Api.health, () => false),
    ]);

    // Backend is reachable if the profiles endpoint responded (even with an empty array).
    // Only fall back to mock data when the network request itself failed.
    const backendReachable = profileResult.value !== null;

    const nextProfileSource: DataSource = backendReachable ? "backend" : "mock";
    const nextProfiles = profileResult.value !== null
      ? ensureOneActive(mapProfiles(profileResult.value))
      : mockProfiles;
    const activeProfile = nextProfiles.find((profile) => profile.active) ?? nextProfiles[0];
    const activeProfileBackendId =
      nextProfileSource === "backend" && activeProfile ? numericBackendId(activeProfile.id) : null;
    const layerResult = activeProfileBackendId
      ? await readOrFallback(() => v2Api.layers(activeProfileBackendId), () => false)
      : { value: null, fallback: true };
    const nextLayerSource: DataSource = backendReachable ? "backend" : "mock";
    const nextLayers = backendReachable
      ? ensureOneActive(mapLayers(layerResult.value ?? []))
      : mockLayers;
    const activeLayer = nextLayers.find((layer) => layer.active) ?? nextLayers[0];
    const activeLayerBackendId =
      nextLayerSource === "backend" && activeLayer ? numericBackendId(activeLayer.id) : null;
    const bindingResult = activeLayerBackendId
      ? await readOrFallback(() => v2Api.bindings(activeLayerBackendId), () => false)
      : { value: null, fallback: true };
    const nextBindings = backendReachable
      ? mapBindings(bindingResult.value ?? [], nextLayers)
      : mockBindings;

    if (options?.signal?.aborted) return;

    setProfiles(nextProfiles);
    setLayers(nextLayers);
    setBindings(nextBindings);
    setProfileSource(nextProfileSource);
    setLayerSource(nextLayerSource);
    setRuns(backendReachable ? mapRuns(runResult.value ?? []) : mockRuns);
    setAutomation((current) => mapAutomation(automationResult.value, null, current));
    if (!backendReachable) {
      setMonitorEvents((current) => (current.length > 0 ? current : mockMonitorEvents));
    }
    setDevices(deviceResult.value ?? []);
    setInputPorts(
      portResult.value ??
        inputResult.value?.available_input_ports?.map((name) => ({
          id: name,
          name,
          online: true,
        })) ??
        [],
    );
    setSelectedInputPortState(inputResult.value?.selected_input_port || null);
    setMidiStatus(healthResult.value?.midi ?? null);
    setDataSourceLabel(backendReachable ? "Real backend data" : "Backend unavailable");
    setError(backendReachable ? null : "Using demo data");
    setLoading(false);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    load({ signal: controller.signal }).catch(() => {
      if (!controller.signal.aborted) {
        setDataSourceLabel("Backend unavailable");
        setError("Using demo data");
        setLoading(false);
      }
    });

    return () => {
      controller.abort();
    };
  }, [load]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let pingTimer: number | null = null;
    const noteTimers = new Map<number, number>();
    let stopped = false;

    const clearNoteTimer = (note: number) => {
      const timer = noteTimers.get(note);
      if (timer !== undefined) window.clearTimeout(timer);
      noteTimers.delete(note);
    };

    const scheduleNoteFade = (note: number) => {
      clearNoteTimer(note);
      const timer = window.setTimeout(() => {
        setLiveNotes((current) => {
          const next = { ...current };
          delete next[note];
          return next;
        });
        noteTimers.delete(note);
      }, 800);
      noteTimers.set(note, timer);
    };

    const connect = () => {
      if (stopped) return;
      socket = new WebSocket(WS_EVENTS_URL);

      socket.onopen = () => {
        if (pingTimer !== null) window.clearInterval(pingTimer);
        pingTimer = window.setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) socket.send("ping");
        }, 25_000);
      };

      socket.onmessage = (message) => {
        let event: V2MidiEventPayload;
        try {
          event = JSON.parse(String(message.data)) as V2MidiEventPayload;
        } catch {
          return;
        }

        const sourcePort = event.source_port_name ?? event.port_name ?? null;
        if (sourcePort) setLiveSourcePort(sourcePort);
        if (event.selected_input_port !== undefined) setSelectedInputPortState(event.selected_input_port || null);

        setLiveLastEvent(formatMidiEvent(event));
        setMonitorEvents((current) => [monitorEventFromPayload(event), ...current].slice(0, 8));

        const matched = Boolean(event.matched_binding_id ?? event.v2_binding_match ?? event.binding_match);
        if (event.matched_binding_id !== undefined && event.matched_binding_id !== null) {
          setLiveMatchedBindingId(String(event.matched_binding_id));
        }

        const note = typeof event.note === "number" ? event.note : null;
        const velocity = typeof event.velocity === "number" ? event.velocity : undefined;
        if (note !== null && event.type === "note_on" && velocity !== 0) {
          clearNoteTimer(note);
          setLiveNotes((current) => ({
            ...current,
            [note]: { active: true, pressed: true, velocity, matched },
          }));
        }
        if (note !== null && (event.type === "note_off" || (event.type === "note_on" && velocity === 0))) {
          setLiveNotes((current) => ({
            ...current,
            [note]: { active: true, pressed: false, matched },
          }));
          scheduleNoteFade(note);
        }

        if (event.type === "control_change" && typeof event.cc === "number") {
          setCcBars((current) => updateCcBars(current, event.cc as number, event.value ?? 0, matched));
        }

        if (
          (event.type === "note_on" && typeof event.velocity === "number" && event.velocity > 0) ||
          event.type === "control_change"
        ) {
          setLastMidiEvent({ ...event });
        }

        if (event.action_execution || event.execution_status) {
          void load({ quiet: true });
        }
      };

      socket.onclose = () => {
        if (pingTimer !== null) {
          window.clearInterval(pingTimer);
          pingTimer = null;
        }
        if (!stopped) {
          reconnectTimer = window.setTimeout(connect, 1500);
        }
      };
    };

    connect();

    return () => {
      stopped = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      if (pingTimer !== null) window.clearInterval(pingTimer);
      noteTimers.forEach((timer) => window.clearTimeout(timer));
      socket?.close();
    };
  }, [load]);

  const setAutomationArmed = useCallback(async (armed: boolean) => {
    const previous = automation;
    setAutomation((current) => ({ ...current, armed }));
    setError(null);
    try {
      const updated = await v2Api.updateAutomation(armed);
      setAutomation((current) => mapAutomation(updated, { matching_mode: current.matchingMode }, current));
    } catch {
      setAutomation(previous);
      setError("Automation update failed");
    }
  }, [automation]);

  const setSelectedInputPort = useCallback(async (portName: string | null) => {
    const previous = selectedInputPort;
    setSelectedInputPortState(portName);
    setError(null);
    try {
      const updated = await v2Api.updateInputSettings(portName);
      setSelectedInputPortState(updated.selected_input_port || null);
    } catch {
      setSelectedInputPortState(previous);
      setError("MIDI input update failed");
    }
  }, [selectedInputPort]);

  const clearRuns = useCallback(async () => {
    setRuns([]);
    try { await v2Api.clearRuns(); }
    catch { await load({ quiet: true }); }
  }, [load]);

  const createProfile = useCallback(async () => {
    if (profileSource !== "backend") return null;
    try {
      const created = await v2Api.createProfile("New Profile");
      const createdId = String(created.id);
      await v2Api.activateProfile(createdId);
      await load({ quiet: true });
      return createdId;
    } catch {
      return null;
    }
  }, [load, profileSource]);

  const renameProfile = useCallback(async (profileId: string, name: string) => {
    const backendId = profileSource === "backend" ? numericBackendId(profileId) : null;
    if (!backendId) return;
    setProfiles((current) => current.map((p) => p.id === profileId ? { ...p, name } : p));
    try {
      await v2Api.updateProfile(backendId, name);
    } catch {
      // revert on error
      await load({ quiet: true });
    }
  }, [load, profileSource]);

  const activateProfile = useCallback(async (profileId: string) => {
    const previousProfiles = profiles;
    setProfiles((current) => current.map((profile) => ({ ...profile, active: profile.id === profileId })));
    setError(null);
    const backendId = profileSource === "backend" ? numericBackendId(profileId) : null;
    if (!backendId) {
      return;
    }
    try {
      await v2Api.activateProfile(backendId);
      await load({ quiet: true });
    } catch {
      setProfiles(previousProfiles);
      setError("Profile activation failed");
    }
  }, [load, profileSource, profiles]);

  const createLayer = useCallback(async () => {
    if (profileSource !== "backend") return null;
    const activeProfile = profiles.find((p) => p.active) ?? profiles[0];
    if (!activeProfile) return null;
    const backendProfileId = numericBackendId(activeProfile.id);
    if (!backendProfileId) return null;
    try {
      const created = await v2Api.createLayer(backendProfileId, "New Layer");
      const createdId = String(created.id);
      await v2Api.activateLayer(createdId);
      await load({ quiet: true });
      return createdId;
    } catch {
      return null;
    }
  }, [load, profileSource, profiles]);

  const renameLayer = useCallback(async (layerId: string, name: string) => {
    const backendId = layerSource === "backend" ? numericBackendId(layerId) : null;
    if (!backendId) return;
    setLayers((current) => current.map((l) => l.id === layerId ? { ...l, name } : l));
    try {
      await v2Api.updateLayer(backendId, name);
    } catch {
      await load({ quiet: true });
    }
  }, [layerSource, load]);

  const activateLayer = useCallback(async (layerId: string) => {
    const previousLayers = layers;
    setLayers((current) => current.map((layer) => ({ ...layer, active: layer.id === layerId })));
    setError(null);
    const backendId = layerSource === "backend" ? numericBackendId(layerId) : null;
    if (!backendId) {
      return;
    }
    try {
      await v2Api.activateLayer(backendId);
      await load({ quiet: true });
    } catch {
      setLayers(previousLayers);
      setError("Layer activation failed");
    }
  }, [layers, layerSource, load]);

  const activeLayer = layers.find((layer) => layer.active) ?? layers[0];
  const activeLayerBackendId = layerSource === "backend" && activeLayer ? numericBackendId(activeLayer.id) : null;
  const canMutateBindings = activeLayerBackendId !== null;

  const createBinding = useCallback(async (payload: BackendBindingCreatePayload) => {
    if (!activeLayerBackendId) {
      throw new Error("Real backend layer required before creating bindings");
    }
    const created = await v2Api.createBinding(activeLayerBackendId, payload);
    const mapped = mapBindings([created], layers)[0];
    await load({ quiet: true });
    return mapped;
  }, [activeLayerBackendId, layers, load]);

  const toggleBindingEnabled = useCallback(async (bindingId: string) => {
    const backendId = numericBackendId(bindingId);
    if (!backendId) return;
    const binding = bindings.find((b) => b.id === bindingId);
    if (!binding) return;
    const newEnabled: 0 | 1 = binding.enabled ? 0 : 1;
    setBindings((current) =>
      current.map((b) => (b.id === bindingId ? { ...b, enabled: !b.enabled } : b))
    );
    try {
      await v2Api.patchBinding(backendId, { enabled: newEnabled });
    } catch {
      await load({ quiet: true });
    }
  }, [bindings, load]);

  const editBinding = useCallback(async (bindingId: string, patch: BackendBindingPatch): Promise<void> => {
    const backendId = numericBackendId(bindingId);
    if (!backendId) throw new Error("Real backend binding required");
    await v2Api.patchBinding(backendId, patch);
    await load({ quiet: true });
  }, [load]);

  const duplicateBinding = useCallback(async (bindingId: string): Promise<V2BindingSummary | null> => {
    const backendId = numericBackendId(bindingId);
    if (!backendId) return null;
    const created = await v2Api.duplicateBinding(backendId);
    await load({ quiet: true });
    return mapBindings([created], layers)[0] ?? null;
  }, [layers, load]);

  const deleteBinding = useCallback(async (bindingId: string) => {
    const backendId = numericBackendId(bindingId);
    if (!backendId) {
      setBindings((current) => current.filter((binding) => binding.id !== bindingId));
      return;
    }
    await v2Api.deleteBinding(backendId);
    await load({ quiet: true });
  }, [load]);

  const deleteProfile = useCallback(async (profileId: string) => {
    const backendId = profileSource === "backend" ? numericBackendId(profileId) : null;
    if (!backendId) return;
    await v2Api.deleteProfile(backendId);
    await load({ quiet: true });
  }, [load, profileSource]);

  const deleteLayer = useCallback(async (layerId: string) => {
    const backendId = layerSource === "backend" ? numericBackendId(layerId) : null;
    if (!backendId) return;
    await v2Api.deleteLayer(backendId);
    await load({ quiet: true });
  }, [layerSource, load]);

  const exportProfile = useCallback(async (profileId: string) => {
    const backendId = numericBackendId(profileId);
    if (!backendId) throw new Error("Real backend profile required for export");
    return v2Api.exportProfile(backendId);
  }, []);

  const importProfile = useCallback(async (payload: BackendProfileExport) => {
    const result = await v2Api.importProfile(payload);
    await load({ quiet: true });
    return result;
  }, [load]);

  const clearMonitorEvents = useCallback(() => {
    setMonitorEvents([]);
    setLiveMatchedBindingId(null);
  }, []);

  const setKeygrab = useCallback(async (enabled: boolean) => {
    setAutomation((current) => ({ ...current, keygrab: enabled }));
    try {
      await v2Api.setKeygrab(enabled);
    } catch {
      setAutomation((current) => ({ ...current, keygrab: !enabled }));
    }
  }, []);

  const setMouseMode = useCallback((mouseMode: boolean) => {
    setAutomation((current) => ({ ...current, mouseMode }));
  }, []);

  const simulateNote = useCallback((note: number, velocity = 80, matched = false, matchedBindingId: string | null = null) => {
    setLiveNotes((current) => ({
      ...current,
      [note]: { active: true, pressed: true, velocity, matched },
    }));
    setLiveMatchedBindingId(matchedBindingId);
    const name = NOTE_NAMES[note % 12] ?? "?";
    const octave = Math.floor(note / 12) - 1;
    const evt: MidiMonitorEvent = {
      id: `sim-${Date.now()}-${note}`,
      port: "Mouse",
      type: "Note On",
      channel: 1,
      value: `${name}${octave} (${note}) · vel ${velocity}`,
      matched,
    };
    setMonitorEvents((current) => [evt, ...current].slice(0, 8));
    window.setTimeout(() => {
      setLiveNotes((current) => {
        const next = { ...current };
        if (next[note]?.pressed) next[note] = { ...next[note], pressed: false };
        return next;
      });
      window.setTimeout(() => {
        setLiveNotes((current) => {
          const next = { ...current };
          delete next[note];
          return next;
        });
      }, 400);
    }, 500);
  }, []);

  const simulateCc = useCallback((controller: number, value: number, matched = false, matchedBindingId: string | null = null) => {
    const boundedValue = Math.max(0, Math.min(127, Math.round(value)));
    setCcBars((current) => updateCcBars(current, controller, boundedValue, matched));
    setLiveMatchedBindingId(matchedBindingId);
    setLastMidiEvent({
      ts: Date.now() / 1000,
      port_name: "Mouse",
      source_port_name: "Mouse",
      type: "control_change",
      channel: 0,
      effective_channel: 0,
      cc: controller,
      value: boundedValue,
      matched_binding_id: matchedBindingId,
    });
    const evt: MidiMonitorEvent = {
      id: `sim-cc-${Date.now()}-${controller}`,
      port: "Mouse",
      type: "CC",
      channel: 1,
      value: `CC ${controller} · ${boundedValue}`,
      matched,
    };
    setMonitorEvents((current) => [evt, ...current].slice(0, 8));
  }, []);

  const dryRunAction = useCallback(async (actionId: string) => {
    const backendId = numericBackendId(actionId);
    if (!backendId) {
      throw new Error("Real backend action required before dry run");
    }
    return v2Api.dryRunAction(backendId);
  }, []);

  const testAction = useCallback(async (actionId: string) => {
    const backendId = numericBackendId(actionId);
    if (!backendId) {
      throw new Error("Real backend action required before test");
    }
    const result = await v2Api.testAction(backendId);
    await load({ quiet: true });
    return result;
  }, [load]);

  const testActionPreview = useCallback(async (payload: BackendActionPreviewPayload) => {
    return v2Api.testActionPreview(payload);
  }, []);

  const keyboardNotes = useMemo(() => {
    const noteColors = new Map<number, NoteDotColor>();
    const noteIconColors = new Map<number, string>();
    const noteIcons = new Map<number, string>();
    for (const b of bindings) {
      if (b.kind === "note" && typeof b.note === "number") {
        noteColors.set(b.note, asDotColor(b.displayColor));
        noteIconColors.set(b.note, displayColorHex(b.displayColor));
        if (b.icon) noteIcons.set(b.note, b.icon);
      }
    }
    const boundNotes = new Set(noteColors.keys());
    const mockNoteMap = new Map(mockKeyboardNotes.map((n) => [n.note, n]));
    return Array.from({ length: 128 }, (_, noteNum) => {
      const mock = mockNoteMap.get(noteNum);
      const live = liveNotes[noteNum];
      const name = NOTE_NAMES[noteNum % 12] ?? "?";
      const octave = Math.floor(noteNum / 12) - 1;
      const bound = (profileSource === "mock" && Boolean(mock?.bound)) || boundNotes.has(noteNum);
      const bindingDotColor = noteColors.get(noteNum) ?? "cyan";
      const baseDots = profileSource === "mock" ? mock?.dots : undefined;
      const dots: KeyboardNote["dots"] = bound && !baseDots?.length ? [bindingDotColor] : baseDots;
      const nextDots: KeyboardNote["dots"] =
        live?.matched && dots && !dots.includes("emerald") ? [...dots, "emerald"] : live?.matched && !dots ? ["emerald"] : dots;
      return {
        note: noteNum,
        label: `${name}${octave}`,
        bound,
        dots: nextDots,
        active: Boolean(live?.active) || Boolean(profileSource === "mock" && mock?.active),
        pressed: Boolean(live?.pressed) || Boolean(profileSource === "mock" && mock?.pressed),
        velocity: live?.velocity ?? (profileSource === "mock" ? mock?.velocity : undefined),
        icon: noteIcons.get(noteNum),
        iconColor: noteIconColors.get(noteNum),
      };
    });
  }, [bindings, liveNotes, profileSource]);

  const appStats = useMemo(() => {
    const baseStats = mapStats(profiles, layers, bindings, devices, mockAppStats);
    return {
      ...baseStats,
      midiInput:
        selectedInputPort ??
        liveSourcePort ??
        midiStatus?.selected_input_port ??
        (profileSource === "backend" ? "Select MIDI Input" : baseStats.midiInput),
      lastEvent: liveLastEvent ?? (profileSource === "backend" ? "Waiting for MIDI input..." : baseStats.lastEvent),
    };
  }, [bindings, devices, layers, liveLastEvent, liveSourcePort, midiStatus?.selected_input_port, profileSource, profiles, selectedInputPort]);

  return {
    profiles,
    layers,
    bindings,
    runs,
    automation,
    appStats,
    monitorEvents,
    keyboardNotes,
    ccBars,
    liveMatchedBindingId,
    lastMidiEvent,
    loading,
    error,
    dataSourceLabel,
    midiStatus,
    inputPorts,
    selectedInputPort,
    setAutomationArmed,
    setSelectedInputPort,
    clearRuns,
    createProfile,
    renameProfile,
    activateProfile,
    createLayer,
    renameLayer,
    activateLayer,
    canMutateBindings,
    createBinding,
    editBinding,
    toggleBindingEnabled,
    duplicateBinding,
    deleteBinding,
    deleteProfile,
    deleteLayer,
    exportProfile,
    importProfile,
    clearMonitorEvents,
    setKeygrab,
    setMouseMode,
    simulateNote,
    simulateCc,
    dryRunAction,
    testAction,
    testActionPreview,
  };
}
