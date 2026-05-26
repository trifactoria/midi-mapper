"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  appStats as mockAppStats,
  automationState as mockAutomationState,
  bindings as mockBindings,
  layers as mockLayers,
  profiles as mockProfiles,
  runs as mockRuns,
} from "./mockData";
import type {
  AppStats,
  AutomationState,
  V2BindingSummary,
  V2LayerSummary,
  V2ProfileSummary,
  V2RunSummary,
} from "./types";
import { mapAutomation, mapBindings, mapLayers, mapProfiles, mapRuns, mapStats } from "./adapters";
import {
  v2Api,
  type BackendActionRunResult,
  type BackendBindingCreatePayload,
  type BackendDevice,
  type BackendMidiStatus,
} from "./api";

type V2ReadData = {
  profiles: V2ProfileSummary[];
  layers: V2LayerSummary[];
  bindings: V2BindingSummary[];
  runs: V2RunSummary[];
  automation: AutomationState;
  appStats: AppStats;
  loading: boolean;
  error: string | null;
  dataSourceLabel: "Real backend data" | "Mock fallback" | "Backend unavailable";
  midiStatus: BackendMidiStatus | null;
  setAutomationArmed: (armed: boolean) => Promise<void>;
  setMatchingMode: (matchingMode: "legacy" | "v2" | "dual") => Promise<void>;
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

export function useV2ReadData(): V2ReadData {
  const [profiles, setProfiles] = useState(mockProfiles);
  const [layers, setLayers] = useState(mockLayers);
  const [bindings, setBindings] = useState(mockBindings);
  const [runs, setRuns] = useState(mockRuns);
  const [automation, setAutomation] = useState(mockAutomationState);
  const [devices, setDevices] = useState<BackendDevice[]>([]);
  const [midiStatus, setMidiStatus] = useState<BackendMidiStatus | null>(null);
  const [profileSource, setProfileSource] = useState<DataSource>("mock");
  const [layerSource, setLayerSource] = useState<DataSource>("mock");
  const [dataSourceLabel, setDataSourceLabel] = useState<V2ReadData["dataSourceLabel"]>("Mock fallback");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (options?: { quiet?: boolean; signal?: AbortSignal }) => {
    if (!options?.quiet) setLoading(true);
    setError(null);

    const [profileResult, runResult, automationResult, matchingResult, deviceResult, healthResult] = await Promise.all([
      readOrFallback(v2Api.profiles, (rows) => rows.length === 0),
      readOrFallback(v2Api.runs, (rows) => rows.length === 0),
      readOrFallback(v2Api.automation, () => false),
      readOrFallback(v2Api.matching, () => false),
      readOrFallback(v2Api.devices, (rows) => rows.length === 0),
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
    setAutomation(mapAutomation(automationResult.value, matchingResult.value, mockAutomationState));
    setDevices(deviceResult.value ?? []);
    setMidiStatus(healthResult.value?.midi ?? null);
    const fallbackCount = [
      profileResult,
      layerResult,
      bindingResult,
      runResult,
      automationResult,
      matchingResult,
      deviceResult,
      healthResult,
    ].filter((result) => result.fallback).length;
    setDataSourceLabel(nextProfileSource === "backend" ? "Real backend data" : fallbackCount === 8 ? "Backend unavailable" : "Mock fallback");
    setError(fallbackCount === 0 ? null : fallbackCount === 8 ? "Using demo data" : "Live data with fallbacks");
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

  const setMatchingMode = useCallback(async (matchingMode: "legacy" | "v2" | "dual") => {
    const previous = automation;
    setAutomation((current) => ({ ...current, matchingMode }));
    setError(null);
    try {
      const updated = await v2Api.updateMatching(matchingMode);
      if (updated.ok === false) throw new Error(updated.error ?? "Matching update failed");
      setAutomation((current) => mapAutomation(null, updated, current));
    } catch {
      setAutomation(previous);
      setError("Matching mode update failed");
    }
  }, [automation]);

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

  const appStats = useMemo(
    () => mapStats(profiles, layers, bindings, devices, mockAppStats),
    [profiles, layers, bindings, devices],
  );

  return {
    profiles,
    layers,
    bindings,
    runs,
    automation,
    appStats,
    loading,
    error,
    dataSourceLabel,
    midiStatus,
    setAutomationArmed,
    setMatchingMode,
    activateProfile,
    activateLayer,
    canMutateBindings,
    createBinding,
    deleteBinding,
    dryRunAction,
    testAction,
  };
}
