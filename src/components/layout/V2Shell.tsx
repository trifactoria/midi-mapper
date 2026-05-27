"use client";

import { useState } from "react";
import { ActionsPanel } from "../bindings/ActionsPanel";
import { BindingsPanel } from "../bindings/BindingsPanel";
import { ConsolePanel } from "../console/ConsolePanel";
import { RunHistoryPanel } from "../history/RunHistoryPanel";
import { MappingTab } from "../mapping/MappingTab";
import { ProfileSidebar, ProfileLayerCompactBar } from "../sidebar/ProfileSidebar";
import { SettingsPanel } from "../settings/SettingsPanel";
import { AutomationTopbar } from "../topbar/AutomationTopbar";
import { useV2ReadData } from "../v2/useV2ReadData";

type TabId = "mapping" | "bindings" | "actions" | "history" | "settings";

const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
  {
    id: "mapping",
    label: "Mapping",
    icon: (
      <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.4">
        <path d="M2 12.5l4-4 2 2 6-6M10 4.5h3.5V8" />
      </svg>
    ),
  },
  {
    id: "bindings",
    label: "Bindings",
    icon: (
      <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.4">
        <path d="M5 8.5l-1.5 1.5a2 2 0 1 0 2.8 2.8L8 11M11 7.5l1.5-1.5a2 2 0 1 0-2.8-2.8L8 5M6 10l4-4" />
      </svg>
    ),
  },
  {
    id: "actions",
    label: "Actions",
    icon: (
      <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.4">
        <path d="M3 8h10M8 3v10" />
      </svg>
    ),
  },
  {
    id: "history",
    label: "Run History",
    icon: (
      <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.4">
        <circle cx="8" cy="8" r="5.5" />
        <path d="M8 5v3l2 2" />
      </svg>
    ),
  },
  {
    id: "settings",
    label: "Settings",
    icon: (
      <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.4">
        <circle cx="8" cy="8" r="2" />
        <path d="M8 1.5v2M8 12.5v2M14.5 8h-2M3.5 8h-2M12.6 3.4l-1.4 1.4M4.8 11.2l-1.4 1.4M12.6 12.6l-1.4-1.4M4.8 4.8 3.4 3.4" />
      </svg>
    ),
  },
];

export function V2Shell() {
  const [activeTab, setActiveTab] = useState<TabId>("mapping");
  const [consoleOpen, setConsoleOpen] = useState(false);
  const {
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
    dataSourceLabel,
    midiStatus,
    inputPorts,
    selectedInputPort,
    setAutomationArmed,
    setSelectedInputPort,
    clearRuns,
    activateProfile,
    activateLayer,
    createProfile,
    renameProfile,
    createLayer,
    renameLayer,
    canMutateBindings,
    createBinding,
    editBinding,
    toggleBindingEnabled,
    duplicateBinding,
    deleteBinding,
    deleteProfile,
    deleteLayer,
    clearMonitorEvents,
    setKeygrab,
    setMouseMode,
    simulateNote,
    dryRunAction,
    testAction,
  } = useV2ReadData();
  const midiUnavailable = midiStatus?.available === false || midiStatus?.degraded === true;
  const midiLabel = selectedInputPort ?? (midiUnavailable ? midiStatus?.message ?? "MIDI unavailable" : appStats.midiInput);

  return (
    <div className="relative min-h-screen w-full overflow-x-hidden bg-[#070a10] text-white">
      {/* Ambient backdrop — deep navy with restrained cyan/purple glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(1400px 520px at 18% -6%, rgba(0,170,210,0.072), transparent 65%), radial-gradient(1100px 460px at 94% -8%, rgba(140,80,220,0.06), transparent 65%), radial-gradient(900px 540px at 50% 112%, rgba(0,170,120,0.035), transparent 65%), linear-gradient(180deg, rgba(7,12,22,0.6), rgba(5,8,15,0.0))",
        }}
      />

      {/* Contained dashboard surface */}
      <div className="relative mx-auto flex min-h-screen w-full max-w-[1840px] flex-col">
        <AutomationTopbar
          state={automation}
          inputPorts={inputPorts}
          selectedInputPort={selectedInputPort}
          onAutomationArmedChange={(armed) => void setAutomationArmed(armed)}
          onSelectedInputPortChange={(portName) => void setSelectedInputPort(portName)}
          onSettingsClick={() => setActiveTab("settings")}
        />

        {/* Mobile profile/layer compact bar */}
        <div className="border-b border-white/10 bg-zinc-950/85 px-3 py-2 lg:hidden">
          <ProfileLayerCompactBar
            profiles={profiles}
            layers={layers}
            onProfileActivate={(profileId) => void activateProfile(profileId)}
            onLayerActivate={(layerId) => void activateLayer(layerId)}
          />
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[224px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)]">
          {/* Left sidebar (lg+) */}
          <div className="hidden lg:block">
            <ProfileSidebar
              profiles={profiles}
              layers={layers}
              onProfileActivate={(profileId) => void activateProfile(profileId)}
              onLayerActivate={(layerId) => void activateLayer(layerId)}
              onCreateProfile={createProfile}
              onCreateLayer={createLayer}
              onRenameProfile={renameProfile}
              onRenameLayer={renameLayer}
              onDeleteProfile={deleteProfile}
              onDeleteLayer={deleteLayer}
            />
          </div>

          {/* Workspace */}
          <div className="flex min-w-0 flex-col">
            {/* Tab bar */}
            <div className="flex items-center gap-0.5 border-b border-white/10 bg-zinc-950/55 px-2 py-1 sm:px-3">
              {tabs.map((tab) => (
                <button
                  type="button"
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={[
                    "relative inline-flex h-8 items-center gap-1.5 rounded-md !px-2.5 !py-0 !text-[11px] font-medium uppercase tracking-[0.10em] transition",
                    activeTab === tab.id
                      ? "text-cyan-100"
                      : "text-white/50 hover:bg-white/[0.04] hover:text-white/85",
                  ].join(" ")}
                >
                  <span className={activeTab === tab.id ? "text-cyan-300" : "text-white/40"}>
                    {tab.icon}
                  </span>
                  {tab.label}
                  {activeTab === tab.id && (
                    <span
                      aria-hidden
                      className="absolute -bottom-1 left-2 right-2 h-0.5 rounded-full bg-cyan-300/90 shadow-[0_0_8px_rgba(0,180,210,0.55)]"
                    />
                  )}
                </button>
              ))}
            </div>

            <main className="min-h-0 flex-1 overflow-y-auto p-2.5 sm:p-3">
              {activeTab === "mapping" && (
                <MappingTab
                  events={monitorEvents}
                  notes={keyboardNotes}
                  bars={ccBars}
                  bindings={bindings}
                  runs={runs}
                  automation={automation}
                  canMutateBindings={canMutateBindings}
                  onCreateBinding={createBinding}
                  onEditBinding={editBinding}
                  onToggleBindingEnabled={(id) => void toggleBindingEnabled(id)}
                  onDuplicateBinding={duplicateBinding}
                  onDryRunAction={dryRunAction}
                  onTestAction={testAction}
                  onDeleteBinding={deleteBinding}
                  onClearRuns={clearRuns}
                  onKeygrabChange={(enabled) => void setKeygrab(enabled)}
                  onMouseModeChange={(mouseMode) => setMouseMode(mouseMode)}
                  onClearEvents={clearMonitorEvents}
                  onSimulateNote={simulateNote}
                  selectedInputPort={selectedInputPort}
                  liveMatchedBindingId={liveMatchedBindingId}
                  lastMidiEvent={lastMidiEvent}
                />
              )}
              {activeTab === "bindings" && <BindingsPanel bindings={bindings} />}
              {activeTab === "actions" && <ActionsPanel bindings={bindings} />}
              {activeTab === "history" && <RunHistoryPanel runs={runs} onClearRuns={clearRuns} />}
              {activeTab === "settings" && (
                <SettingsPanel
                  automation={automation}
                  selectedInputPort={selectedInputPort}
                  inputPorts={inputPorts}
                  midiStatus={midiStatus}
                  dataSourceLabel={dataSourceLabel}
                  onAutomationArmedChange={(armed) => void setAutomationArmed(armed)}
                  onKeygrabChange={(enabled) => void setKeygrab(enabled)}
                  onMouseModeChange={(mouseMode) => setMouseMode(mouseMode)}
                  onSelectedInputPortChange={(portName) => void setSelectedInputPort(portName)}
                />
              )}
            </main>
          </div>
        </div>

        {/* Status footer */}
        <footer className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/10 bg-zinc-950/85 px-3 py-1.5 text-[10.5px] text-white/55 backdrop-blur sm:px-4">
          <span className="inline-flex items-center gap-1.5">
            <span
              className={[
                "h-1.5 w-1.5 rounded-full",
                midiUnavailable
                  ? "bg-amber-300 shadow-[0_0_6px_rgba(252,211,77,0.65)]"
                  : "bg-emerald-300 shadow-[0_0_6px_rgba(52,211,153,0.7)]",
              ].join(" ")}
            />
            <span className="uppercase tracking-[0.12em] text-white/40">MIDI Input</span>
            <span className="font-mono text-white/80">{midiLabel}</span>
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="uppercase tracking-[0.12em] text-white/40">Last Event</span>
            <span className="font-mono text-white/80">
              {loading ? "Loading backend..." : appStats.lastEvent}
            </span>
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="uppercase tracking-[0.12em] text-white/40">Data</span>
            <span className="font-mono text-white/80">{dataSourceLabel}</span>
          </span>
          <span className="ml-auto inline-flex items-center gap-3.5 font-mono text-white/65 tabular-nums">
            <span>
              <span className="text-white/35">Profiles</span> {appStats.profiles}
            </span>
            <span>
              <span className="text-white/35">Layers</span> {appStats.layers}
            </span>
            <span>
              <span className="text-white/35">Bindings</span> {appStats.bindings}
            </span>
            <span>
              <span className="text-white/35">Actions</span> {appStats.actions}
            </span>
          </span>
          <button
            type="button"
            onClick={() => setConsoleOpen((o) => !o)}
            className={[
              "ml-1 inline-flex !h-6 items-center gap-1.5 rounded-md border !px-2 !text-[10.5px] transition",
              consoleOpen
                ? "border-cyan-300/25 text-cyan-200 shadow-[inset_0_0_0_1px_rgba(0,180,210,0.12)]"
                : "border-white/10 text-white/80 hover:bg-white/[0.06]",
            ].join(" ")}
            style={{ background: consoleOpen ? "rgba(0,180,210,0.07)" : "rgba(255,255,255,0.04)" }}
          >
            <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="2.5" y="3" width="11" height="10" rx="1.2" />
              <path d="M5 7l1.5 1.5L5 10M8.5 10h2.5" />
            </svg>
            Console
          </button>
        </footer>
        {consoleOpen && (
          <ConsolePanel
            runs={runs}
            onClose={() => setConsoleOpen(false)}
            onClearRuns={clearRuns}
          />
        )}
      </div>
    </div>
  );
}
