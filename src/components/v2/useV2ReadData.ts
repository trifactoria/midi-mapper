"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  appStats as mockAppStats,
  automationState as mockAutomationState,
  bindings as mockBindings,
  ccBars as mockCcBars,
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
  V2BindingSummary,
  V2LayerSummary,
  V2MidiEventPayload,
  V2ProfileSummary,
  V2RunSummary,
} from "./types";
import { mapAutomation, mapBindings, mapLayers, mapProfiles, mapRuns, mapStats } from "./adapters";
import {
  v2Api,
  type BackendActionRunResult,
  type BackendBindingCreatePayload,
  type BackendDevice,
  type BackendPort,
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
  loading: boolean;
  error: string | null;
  dataSourceLabel: "Real backend data" | "Mock fallback" | "Backend unavailable";
  midiStatus: BackendMidiStatus | null;
  inputPorts: BackendPort[];
  selectedInputPort: string | null;
  setAutomationArmed: (armed: boolean) => Promise<void>;
  setSelectedInputPort: (portName: string | null) => Promise<void>;
  activateProfile: (profileId: string) => Promise<void>;
  activateLayer: (layerId: string) => Promise<void>;
  canMutateBindings: boolean;
  createBinding: (payload: BackendBindingCreatePayload) => Promise<V2BindingSummary>;
  deleteBinding: (bindingId: string) => Promise<void>;
  dryRunAction: (actionId: string) => Promise<BackendActionRunResult>;
  testAction: (actionId: string) => Promise<BackendActionRunResult>;
};

type ReadResult<T> = {
  value: T | null;
  fallback: boolean;
};

type DataSource = "backend" | "mock";
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

  const replacementIndex = current.findIndex((bar) => bar.value === 0);
  const next = [...current];
  next[replacementIndex >= 0 ? replacementIndex : next.length - 1] = { index: cc, value: boundedValue, color };
  return next;
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
  const [dataSourceLabel, setDataSourceLabel] = useState<V2ReadData["dataSourceLabel"]>("Mock fallback");
  const [monitorEvents, setMonitorEvents] = useState<MidiMonitorEvent[]>(mockMonitorEvents);
  const [liveNotes, setLiveNotes] = useState<LiveNoteState>({});
  const [ccBars, setCcBars] = useState<CcBar[]>(mockCcBars);
  const [liveSourcePort, setLiveSourcePort] = useState<string | null>(null);
  const [liveLastEvent, setLiveLastEvent] = useState<string | null>(null);
  const [liveMatchedBindingId, setLiveMatchedBindingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (options?: { quiet?: boolean; signal?: AbortSignal }) => {
    if (!options?.quiet) setLoading(true);
    setError(null);

    const [profileResult, runResult, automationResult, deviceResult, portResult, inputResult, healthResult] = await Promise.all([
      readOrFallback(v2Api.profiles, (rows) => rows.length === 0),
      readOrFallback(v2Api.runs, (rows) => rows.length === 0),
      readOrFallback(v2Api.automation, () => false),
      readOrFallback(v2Api.devices, (rows) => rows.length === 0),
      readOrFallback(v2Api.ports, (rows) => rows.length === 0),
      readOrFallback(v2Api.inputSettings, () => false),
      readOrFallback(v2Api.health, () => false),
    ]);

    const nextProfileSource: DataSource = profileResult.value ? "backend" : "mock";
    const nextProfiles = profileResult.value ? ensureOneActive(mapProfiles(profileResult.value)) : mockProfiles;
    const activeProfile = nextProfiles.find((profile) => profile.active) ?? nextProfiles[0];
    const activeProfileBackendId =
      nextProfileSource === "backend" && activeProfile ? numericBackendId(activeProfile.id) : null;
    const layerResult = activeProfileBackendId
      ? await readOrFallback(() => v2Api.layers(activeProfileBackendId), (rows) => rows.length === 0)
      : { value: null, fallback: true };
    const nextLayerSource: DataSource = layerResult.value ? "backend" : "mock";
    const nextLayers = layerResult.value ? ensureOneActive(mapLayers(layerResult.value)) : mockLayers;
    const activeLayer = nextLayers.find((layer) => layer.active) ?? nextLayers[0];
    const activeLayerBackendId =
      nextLayerSource === "backend" && activeLayer ? numericBackendId(activeLayer.id) : null;
    const bindingResult = activeLayerBackendId
      ? await readOrFallback(() => v2Api.bindings(activeLayerBackendId), (rows) => rows.length === 0)
      : { value: null, fallback: true };
    const nextBindings = bindingResult.value ? mapBindings(bindingResult.value, nextLayers) : mockBindings;

    if (options?.signal?.aborted) return;

    setProfiles(nextProfiles);
    setLayers(nextLayers);
    setBindings(nextBindings);
    setProfileSource(nextProfileSource);
    setLayerSource(nextLayerSource);
    setRuns(runResult.value ? mapRuns(runResult.value) : mockRuns);
    setAutomation(mapAutomation(automationResult.value, null, mockAutomationState));
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
    const fallbackCount = [
      profileResult,
      layerResult,
      bindingResult,
      runResult,
      automationResult,
      deviceResult,
      portResult,
      inputResult,
      healthResult,
    ].filter((result) => result.fallback).length;
    setDataSourceLabel(nextProfileSource === "backend" ? "Real backend data" : fallbackCount === 9 ? "Backend unavailable" : "Mock fallback");
    setError(fallbackCount === 0 ? null : fallbackCount === 9 ? "Using demo data" : "Live data with fallbacks");
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

  const deleteBinding = useCallback(async (bindingId: string) => {
    const backendId = numericBackendId(bindingId);
    if (!backendId) {
      setBindings((current) => current.filter((binding) => binding.id !== bindingId));
      return;
    }
    await v2Api.deleteBinding(backendId);
    await load({ quiet: true });
  }, [load]);

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

  const keyboardNotes = useMemo(() => {
    const boundNotes = new Set(bindings.filter((binding) => binding.kind === "note" && typeof binding.note === "number").map((binding) => binding.note as number));
    return mockKeyboardNotes.map((note) => {
      const live = liveNotes[note.note];
      const bound = note.bound || boundNotes.has(note.note);
      const dots: KeyboardNote["dots"] = bound && !note.dots?.length ? ["cyan"] : note.dots;
      const nextDots: KeyboardNote["dots"] =
        live?.matched && dots && !dots.includes("emerald") ? [...dots, "emerald"] : live?.matched && !dots ? ["emerald"] : dots;
      return {
        ...note,
        bound,
        dots: nextDots,
        active: Boolean(live?.active) || Boolean(profileSource === "mock" && note.active),
        pressed: Boolean(live?.pressed) || Boolean(profileSource === "mock" && note.pressed),
        velocity: live?.velocity ?? (profileSource === "mock" ? note.velocity : undefined),
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
    loading,
    error,
    dataSourceLabel,
    midiStatus,
    inputPorts,
    selectedInputPort,
    setAutomationArmed,
    setSelectedInputPort,
    activateProfile,
    activateLayer,
    canMutateBindings,
    createBinding,
    deleteBinding,
    dryRunAction,
    testAction,
  };
}
