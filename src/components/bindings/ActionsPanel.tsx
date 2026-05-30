"use client";

import { useMemo, useState } from "react";
import type { V2ActionStep, V2BindingSummary, V2Macro } from "../v2/types";

type NativeStepType = "command" | "notification" | "open_url" | "open_app" | "hotkey";

type CommandPayload = {
  type?: NativeStepType;
  label?: string;
  command?: string;
  workingDirectory?: string;
  executionMode?: "argv" | "detached";
  timeoutMs?: number;
  title?: string;
  message?: string;
  urgency?: string;
};

type StepPatch = Partial<CommandPayload> & { durationMs?: number };

type Props = {
  bindings: V2BindingSummary[];
  macros: V2Macro[];
  onAddDelayStep?: (bindingId: string) => void;
  onAddCommandStep?: (bindingId: string, payload: CommandPayload) => void;
  onUpdateStep?: (bindingId: string, bindingActionId: string, patch: StepPatch) => void;
  onDeleteStep?: (bindingId: string, bindingActionId: string) => void;
  onMoveStep?: (bindingId: string, bindingActionId: string, direction: "up" | "down") => void;
  onToggleStep?: (bindingId: string, bindingActionId: string, enabled: boolean) => void;
  onSaveMacro?: (bindingId: string, name: string) => Promise<void>;
  onApplyMacro?: (macroId: string, bindingId: string, replaceExisting: boolean) => Promise<void>;
  onDeleteMacro?: (macroId: string) => Promise<void>;
  onCloneBinding?: (bindingId: string, targetNote: number | null, targetController: number | null, targetChannel: number | null) => Promise<void>;
};

type TriggerGroup = {
  key: string;
  label: string;
  kind: "note" | "cc";
  note?: number;
  channel?: number;
  controller?: number;
  bindings: V2BindingSummary[];
  steps: V2ActionStep[];
  primaryBindingId: string;
};

function triggerKey(binding: V2BindingSummary): string {
  return [
    binding.layer,
    binding.kind,
    binding.channel ?? "",
    binding.note ?? "",
    binding.controller ?? "",
    binding.velocityMin ?? "",
    binding.velocityMax ?? "",
    binding.valueMin ?? "",
    binding.valueMax ?? "",
  ].join("|");
}

function stepSummary(step: V2ActionStep): string {
  if (step.type === "delay") return `Wait ${step.durationMs ?? 0}ms`;
  if (step.type === "notification") return `Notify: ${step.title?.trim() || step.label || "Notification"}`;
  if (step.type === "open_url") return `Open URL: ${step.command || ""}`;
  if (step.type === "open_app") return `Open App: ${(step.command || "").split(" ")[0] || step.label || "app"}`;
  if (step.type === "hotkey") return `Hotkey: ${step.command || step.label || ""}`;
  return step.command || step.label || "Command";
}

function commandWithArgs(command: string, args: string): string {
  return [command.trim(), args.trim()].filter(Boolean).join(" ");
}

function StepTypeBadge({ step }: { step: V2ActionStep }) {
  if (step.type === "delay") {
    return <span className="rounded bg-purple-300/[0.1] !px-1.5 !py-px text-[9.5px] text-purple-200/70">wait</span>;
  }
  if (step.type === "notification") {
    return <span className="rounded bg-emerald-300/[0.1] !px-1.5 !py-px text-[9.5px] text-emerald-200/70">notify</span>;
  }
  if (step.type === "open_url") {
    return <span className="rounded bg-sky-300/[0.1] !px-1.5 !py-px text-[9.5px] text-sky-200/70">url</span>;
  }
  if (step.type === "open_app") {
    return <span className="rounded bg-amber-300/[0.1] !px-1.5 !py-px text-[9.5px] text-amber-200/70">app</span>;
  }
  if (step.type === "hotkey") {
    return <span className="rounded bg-violet-300/[0.1] !px-1.5 !py-px text-[9.5px] text-violet-200/70">key</span>;
  }
  if (step.executionMode === "detached") {
    return <span className="rounded bg-amber-300/[0.08] !px-1.5 !py-px text-[9.5px] text-amber-200/60">detached</span>;
  }
  return <span className="rounded bg-cyan-300/[0.07] !px-1.5 !py-px text-[9.5px] text-cyan-200/55">cmd</span>;
}

function MacroDrawer({
  groupKey,
  primaryBindingId,
  macros,
  onSaveMacro,
  onApplyMacro,
  onDeleteMacro,
  onClose,
}: {
  groupKey: string;
  primaryBindingId: string;
  macros: V2Macro[];
  onSaveMacro?: (bindingId: string, name: string) => Promise<void>;
  onApplyMacro?: (macroId: string, bindingId: string, replaceExisting: boolean) => Promise<void>;
  onDeleteMacro?: (macroId: string) => Promise<void>;
  onClose: () => void;
}) {
  const [saveName, setSaveName] = useState("");
  const [saving, setSaving] = useState(false);
  const [applying, setApplying] = useState<string | null>(null);

  const handleSave = async () => {
    if (!saveName.trim() || !onSaveMacro) return;
    setSaving(true);
    try {
      await onSaveMacro(primaryBindingId, saveName.trim());
      setSaveName("");
    } finally {
      setSaving(false);
    }
  };

  const handleApply = async (macroId: string, replace: boolean) => {
    if (!onApplyMacro) return;
    setApplying(macroId);
    try {
      await onApplyMacro(macroId, primaryBindingId, replace);
      onClose();
    } finally {
      setApplying(null);
    }
  };

  return (
    <div className="mt-2 rounded border border-cyan-300/15 bg-cyan-300/[0.03] p-2.5">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[10.5px] font-semibold uppercase tracking-[0.10em] text-cyan-100/70">
          Macros / Templates
        </span>
        <button type="button" onClick={onClose} className="text-[10px] text-white/30 hover:text-white/60" style={{ background: "transparent", border: "none", padding: 0 }}>
          close
        </button>
      </div>

      {/* Save current sequence as macro */}
      <div className="mb-2 flex gap-1">
        <input
          value={saveName}
          onChange={(e) => setSaveName(e.target.value)}
          placeholder="Macro name…"
          className="flex-1 !h-7 !text-[10.5px]"
          onKeyDown={(e) => { if (e.key === "Enter") void handleSave(); }}
        />
        <button
          type="button"
          disabled={!saveName.trim() || saving}
          className="!h-7 !rounded !px-2 !py-0 !text-[10px]"
          onClick={() => void handleSave()}
        >
          Save
        </button>
      </div>

      {/* Existing macros */}
      {macros.length === 0 ? (
        <p className="text-[10px] text-white/30">No saved macros yet.</p>
      ) : (
        <div className="space-y-1">
          {macros.map((macro) => (
            <div key={macro.id} className="flex items-center gap-1.5 rounded border border-white/[0.06] bg-white/[0.02] !px-2 !py-1">
              <div className="min-w-0 flex-1">
                <div className="truncate text-[11px] text-white/80">{macro.name}</div>
                <div className="text-[9.5px] text-white/35">{macro.stepCount} step{macro.stepCount === 1 ? "" : "s"}</div>
              </div>
              <button
                type="button"
                disabled={applying === macro.id}
                className="!h-6 !rounded !px-1.5 !py-0 !text-[10px] text-cyan-200"
                onClick={() => void handleApply(macro.id, false)}
                title="Append macro steps to this sequence"
              >
                Append
              </button>
              <button
                type="button"
                disabled={applying === macro.id}
                className="!h-6 !rounded !px-1.5 !py-0 !text-[10px] text-amber-200"
                onClick={() => void handleApply(macro.id, true)}
                title="Replace this sequence with macro steps"
              >
                Replace
              </button>
              <button
                type="button"
                className="!h-6 !rounded !px-1.5 !py-0 !text-[10px] text-rose-300/70"
                onClick={() => void onDeleteMacro?.(macro.id)}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CloneDrawer({
  group,
  onCloneBinding,
  onClose,
}: {
  group: TriggerGroup;
  onCloneBinding?: Props["onCloneBinding"];
  onClose: () => void;
}) {
  const isNote = group.kind === "note";
  const [targetValue, setTargetValue] = useState(
    isNote ? String(group.note ?? "") : String(group.controller ?? "")
  );
  const [targetChannel, setTargetChannel] = useState(String(group.channel ?? ""));
  const [cloning, setCloning] = useState(false);

  const handleClone = async () => {
    if (!onCloneBinding) return;
    const parsedValue = targetValue.trim() ? parseInt(targetValue, 10) : null;
    const parsedChannel = targetChannel.trim() ? parseInt(targetChannel, 10) : null;
    const targetNote = isNote ? parsedValue : null;
    const targetController = !isNote ? parsedValue : null;
    setCloning(true);
    try {
      await onCloneBinding(group.primaryBindingId, targetNote, targetController, parsedChannel);
      onClose();
    } finally {
      setCloning(false);
    }
  };

  return (
    <div className="mt-2 rounded border border-amber-300/15 bg-amber-300/[0.03] p-2.5">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[10.5px] font-semibold uppercase tracking-[0.10em] text-amber-100/70">
          Clone Sequence To Key
        </span>
        <button type="button" onClick={onClose} className="text-[10px] text-white/30 hover:text-white/60" style={{ background: "transparent", border: "none", padding: 0 }}>
          close
        </button>
      </div>
      <div className="flex gap-1.5">
        <div className="flex flex-col gap-0.5">
          <label className="text-[9.5px] text-white/40">{isNote ? "Target Note" : "Target CC"}</label>
          <input
            type="number"
            min={0}
            max={127}
            value={targetValue}
            onChange={(e) => setTargetValue(e.target.value)}
            className="!h-7 w-20 !text-[10.5px]"
            placeholder="0-127"
          />
        </div>
        <div className="flex flex-col gap-0.5">
          <label className="text-[9.5px] text-white/40">Channel</label>
          <input
            type="number"
            min={0}
            max={15}
            value={targetChannel}
            onChange={(e) => setTargetChannel(e.target.value)}
            className="!h-7 w-16 !text-[10.5px]"
            placeholder="0-15"
          />
        </div>
        <div className="flex items-end">
          <button
            type="button"
            disabled={cloning || !targetValue.trim()}
            className="!h-7 !rounded !px-2 !py-0 !text-[10px]"
            onClick={() => void handleClone()}
          >
            Clone (disabled)
          </button>
        </div>
      </div>
      <p className="mt-1.5 text-[9.5px] text-white/30">
        Creates a disabled copy of this trigger sequence on the target key.
      </p>
    </div>
  );
}

export function ActionsPanel({
  bindings,
  macros,
  onAddDelayStep,
  onAddCommandStep,
  onUpdateStep,
  onDeleteStep,
  onMoveStep,
  onToggleStep,
  onSaveMacro,
  onApplyMacro,
  onDeleteMacro,
  onCloneBinding,
}: Props) {
  const [addGroupKey, setAddGroupKey] = useState<string | null>(null);
  const [editingStepKey, setEditingStepKey] = useState<string | null>(null);
  const [macroDrawerKey, setMacroDrawerKey] = useState<string | null>(null);
  const [cloneDrawerKey, setCloneDrawerKey] = useState<string | null>(null);
  const [form, setForm] = useState({
    stepType: "command" as NativeStepType,
    label: "",
    command: "",
    args: "",
    workingDirectory: "",
    executionMode: "argv" as "argv" | "detached",
    timeoutMs: "",
    durationMs: "3000",
    title: "",
    message: "",
    urgency: "",
  });

  const groups = useMemo<TriggerGroup[]>(() => {
    const byKey = new Map<string, TriggerGroup>();
    for (const binding of bindings) {
      const key = triggerKey(binding);
      const existing = byKey.get(key);
      const group: TriggerGroup =
        existing ??
        {
          key,
          label: `Ch ${(binding.channel ?? 0) + 1} · ${binding.triggerLabel}${binding.triggerCondition ? ` · ${binding.triggerCondition}` : ""}`,
          kind: binding.kind,
          note: binding.note,
          channel: binding.channel,
          controller: binding.controller,
          bindings: [],
          steps: [],
          primaryBindingId: binding.id,
        };
      group.bindings.push(binding);
      group.steps.push(...(binding.actions ?? []));
      byKey.set(key, group);
    }
    return [...byKey.values()].map((group) => ({
      ...group,
      steps: group.steps.sort(
        (a, b) =>
          a.executionOrder - b.executionOrder ||
          Number(a.bindingId || 0) - Number(b.bindingId || 0) ||
          Number(a.bindingActionId) - Number(b.bindingActionId),
      ),
    }));
  }, [bindings]);

  const steps = groups.flatMap((group) => group.steps);
  const enabledCount = steps.filter((step) => step.enabled).length;

  const resetForm = () => {
    setForm((f) => ({ ...f, label: "", command: "", args: "", workingDirectory: "", executionMode: "argv", timeoutMs: "", durationMs: "3000", title: "", message: "", urgency: "" }));
  };

  const startEdit = (step: V2ActionStep) => {
    setEditingStepKey(step.bindingActionId);
    setAddGroupKey(null);
    setForm({
      stepType: (step.type as NativeStepType) ?? "command",
      label: step.label,
      command: step.command ?? "",
      args: "",
      workingDirectory: step.workingDirectory ?? "",
      executionMode: step.executionMode === "detached" ? "detached" : "argv",
      timeoutMs: step.timeoutMs == null ? "" : String(step.timeoutMs),
      durationMs: String(step.durationMs ?? 3000),
      title: step.title ?? "",
      message: step.message ?? "",
      urgency: step.urgency ?? "",
    });
  };

  const submitCommand = (bindingId: string) => {
    const t = form.stepType;
    if (t === "notification") {
      if (!form.title.trim()) return;
      onAddCommandStep?.(bindingId, {
        type: "notification",
        label: form.label || `Notify: ${form.title.trim()}`,
        title: form.title.trim(),
        message: form.message.trim() || undefined,
        urgency: form.urgency || undefined,
      });
    } else {
      const command = commandWithArgs(form.command, form.args);
      if (!command) return;
      onAddCommandStep?.(bindingId, {
        type: t,
        label: form.label || undefined,
        command,
        workingDirectory: form.workingDirectory || undefined,
        executionMode: t === "open_url" || t === "open_app" ? "detached" : form.executionMode,
        timeoutMs: form.timeoutMs ? Number(form.timeoutMs) : undefined,
      });
    }
    setAddGroupKey(null);
    resetForm();
  };

  const submitEdit = (step: V2ActionStep) => {
    let patch: StepPatch;
    if (step.type === "delay") {
      patch = { durationMs: Number(form.durationMs || 0), label: form.label };
    } else if (step.type === "notification") {
      patch = {
        label: form.label || `Notify: ${form.title.trim()}`,
        title: form.title.trim() || undefined,
        message: form.message.trim() || undefined,
        urgency: form.urgency || undefined,
      };
    } else {
      patch = {
        label: form.label,
        command: commandWithArgs(form.command, form.args),
        workingDirectory: form.workingDirectory || undefined,
        executionMode: form.executionMode,
        timeoutMs: form.timeoutMs ? Number(form.timeoutMs) : undefined,
      };
    }
    onUpdateStep?.(step.bindingId, step.bindingActionId, patch);
    setEditingStepKey(null);
    resetForm();
  };

  return (
    <section className="rounded-md border border-white/8 bg-white/[0.014] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.018),inset_0_0_24px_rgba(0,0,0,0.18)]">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/65">
          Actions
          <span className="rounded bg-white/[0.06] !px-1 !py-px font-mono text-[10px] text-white/60">
            {groups.length}
          </span>
        </h3>
        <div className="flex shrink-0 items-center gap-1 font-mono text-[10px]">
          <span className="rounded border border-white/10 bg-white/[0.04] px-1.5 py-px text-white/45">{steps.length} steps</span>
          <span className="rounded border border-emerald-300/15 bg-emerald-300/[0.05] px-1.5 py-px text-emerald-200/60">{enabledCount} enabled</span>
          {macros.length > 0 && (
            <span className="rounded border border-cyan-300/15 bg-cyan-300/[0.04] px-1.5 py-px text-cyan-200/60">{macros.length} macros</span>
          )}
        </div>
      </div>

      {groups.length === 0 ? (
        <p className="py-4 text-center text-[11px] text-white/30">No actions yet — create bindings from the Mapping tab.</p>
      ) : (
        <div className="grid gap-2.5">
          {groups.map((group) => {
            const targetBindingId = group.primaryBindingId;
            const showMacros = macroDrawerKey === group.key;
            const showClone = cloneDrawerKey === group.key;
            return (
              <div key={group.key} className="rounded-md border border-white/8 bg-white/[0.02] p-2.5">
                {/* Trigger header */}
                <div className="mb-2.5 flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      {/* Kind badge */}
                      <span className={[
                        "shrink-0 rounded !px-1.5 !py-px text-[9.5px] uppercase tracking-[0.08em]",
                        group.kind === "cc"
                          ? "bg-purple-300/[0.09] text-purple-200/70"
                          : "bg-cyan-300/[0.07] text-cyan-200/60",
                      ].join(" ")}>
                        {group.kind === "cc" ? "CC" : "Note"}
                      </span>
                      <span className="truncate text-sm font-semibold text-white">{group.label}</span>
                    </div>
                    <div className="mt-0.5 text-[10px] text-white/35">
                      {group.bindings.length} binding{group.bindings.length === 1 ? "" : "s"} · {group.steps.length} step{group.steps.length === 1 ? "" : "s"}
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-1">
                    <button
                      type="button"
                      className="!h-6 rounded-md border border-white/10 !px-2 !text-[10.5px] text-cyan-200 hover:text-cyan-100"
                      style={{ background: "rgba(0,180,210,0.06)" }}
                      onClick={() => {
                        setAddGroupKey(addGroupKey === group.key ? null : group.key);
                        setEditingStepKey(null);
                        resetForm();
                      }}
                    >
                      + cmd
                    </button>
                    <button
                      type="button"
                      className="!h-6 rounded-md border border-white/10 !px-2 !text-[10.5px] text-white/55 hover:text-white/80"
                      style={{ background: "rgba(255,255,255,0.03)" }}
                      onClick={() => targetBindingId && onAddDelayStep?.(targetBindingId)}
                    >
                      + wait
                    </button>
                    <button
                      type="button"
                      title="Macros / Templates"
                      className={[
                        "!h-6 rounded-md border !px-2 !text-[10.5px] transition",
                        showMacros
                          ? "border-cyan-300/25 text-cyan-200"
                          : "border-white/10 text-white/45 hover:text-white/75",
                      ].join(" ")}
                      style={{ background: showMacros ? "rgba(0,180,210,0.07)" : "rgba(255,255,255,0.03)" }}
                      onClick={() => {
                        setMacroDrawerKey(showMacros ? null : group.key);
                        setCloneDrawerKey(null);
                      }}
                    >
                      Macros
                    </button>
                    <button
                      type="button"
                      title="Clone sequence to another key"
                      className={[
                        "!h-6 rounded-md border !px-2 !text-[10.5px] transition",
                        showClone
                          ? "border-amber-300/25 text-amber-200"
                          : "border-white/10 text-white/45 hover:text-white/75",
                      ].join(" ")}
                      style={{ background: showClone ? "rgba(251,191,36,0.07)" : "rgba(255,255,255,0.03)" }}
                      onClick={() => {
                        setCloneDrawerKey(showClone ? null : group.key);
                        setMacroDrawerKey(null);
                      }}
                    >
                      Clone
                    </button>
                  </div>
                </div>

                {/* Add step form */}
                {addGroupKey === group.key && targetBindingId && (
                  <div className="mb-2 rounded border border-cyan-300/15 bg-cyan-300/[0.04] p-2 space-y-1.5">
                    <div className="flex flex-wrap gap-1.5 items-center">
                      <select
                        value={form.stepType}
                        onChange={(e) => setForm((c) => ({ ...c, stepType: e.target.value as NativeStepType }))}
                        className="!h-7 !text-[10px] !py-0"
                      >
                        <option value="command">Command</option>
                        <option value="notification">Notification</option>
                        <option value="open_url">Open URL</option>
                        <option value="open_app">Open App</option>
                        <option value="hotkey">Hotkey</option>
                      </select>
                      <input value={form.label} onChange={(e) => setForm((c) => ({ ...c, label: e.target.value }))} placeholder="Label (optional)" className="!h-7 flex-1 !text-[10px]" />
                    </div>
                    {form.stepType === "notification" ? (
                      <div className="flex flex-wrap gap-1.5">
                        <input value={form.title} onChange={(e) => setForm((c) => ({ ...c, title: e.target.value }))} placeholder="Title *" className="!h-7 flex-1 !text-[10px]" />
                        <input value={form.message} onChange={(e) => setForm((c) => ({ ...c, message: e.target.value }))} placeholder="Body" className="!h-7 flex-1 !text-[10px]" />
                        <select value={form.urgency} onChange={(e) => setForm((c) => ({ ...c, urgency: e.target.value }))} className="!h-7 !text-[10px] !py-0">
                          <option value="">Urgency</option>
                          <option value="low">Low</option>
                          <option value="normal">Normal</option>
                          <option value="critical">Critical</option>
                        </select>
                      </div>
                    ) : (
                      <div className="flex flex-wrap gap-1.5">
                        <input
                          value={form.command}
                          onChange={(e) => setForm((c) => ({ ...c, command: e.target.value }))}
                          placeholder={form.stepType === "open_url" ? "URL" : form.stepType === "hotkey" ? "Shortcut (e.g. ctrl+alt+t)" : "Command"}
                          className="!h-7 flex-1 !text-[10px]"
                        />
                        {form.stepType === "command" && (
                          <>
                            <input value={form.args} onChange={(e) => setForm((c) => ({ ...c, args: e.target.value }))} placeholder="Arguments" className="!h-7 flex-1 !text-[10px]" />
                            <input value={form.workingDirectory} onChange={(e) => setForm((c) => ({ ...c, workingDirectory: e.target.value }))} placeholder="Working dir" className="!h-7 flex-1 !text-[10px]" />
                          </>
                        )}
                        {form.stepType === "open_app" && (
                          <input value={form.args} onChange={(e) => setForm((c) => ({ ...c, args: e.target.value }))} placeholder="Arguments (optional)" className="!h-7 flex-1 !text-[10px]" />
                        )}
                      </div>
                    )}
                    <div className="flex gap-1">
                      <button type="button" className="!h-7 !px-2 !py-0 !text-[10px]" onClick={() => submitCommand(targetBindingId)}>Save</button>
                      <button type="button" className="!h-7 !px-2 !py-0 !text-[10px]" onClick={() => setAddGroupKey(null)}>Cancel</button>
                    </div>
                  </div>
                )}

                {/* Macros drawer */}
                {showMacros && (
                  <MacroDrawer
                    groupKey={group.key}
                    primaryBindingId={targetBindingId}
                    macros={macros}
                    onSaveMacro={onSaveMacro}
                    onApplyMacro={onApplyMacro}
                    onDeleteMacro={onDeleteMacro}
                    onClose={() => setMacroDrawerKey(null)}
                  />
                )}

                {/* Clone drawer */}
                {showClone && (
                  <CloneDrawer
                    group={group}
                    onCloneBinding={onCloneBinding}
                    onClose={() => setCloneDrawerKey(null)}
                  />
                )}

                {/* Steps list */}
                <div className="mt-2 grid gap-1.5">
                  {group.steps.length === 0 && (
                    <div className="rounded border border-white/5 bg-white/[0.02] px-2 py-2 text-xs text-white/35">
                      No steps in this trigger sequence.
                    </div>
                  )}
                  {group.steps.map((step, index) => (
                    <div
                      key={step.bindingActionId}
                      className={[
                        "rounded border bg-white/[0.025] p-2 transition",
                        step.enabled ? "border-white/10" : "border-white/[0.05] opacity-60",
                      ].join(" ")}
                    >
                      {editingStepKey === step.bindingActionId ? (
                        <div className="space-y-1.5">
                          <div className="flex flex-wrap gap-1.5">
                            <input value={form.label} onChange={(e) => setForm((c) => ({ ...c, label: e.target.value }))} placeholder="Label" className="!h-7 flex-1 !text-[10px]" />
                          </div>
                          {step.type === "delay" ? (
                            <input type="number" value={form.durationMs} onChange={(e) => setForm((c) => ({ ...c, durationMs: e.target.value }))} placeholder="Duration ms" className="!h-7 !text-[10px]" />
                          ) : step.type === "notification" ? (
                            <div className="flex flex-wrap gap-1.5">
                              <input value={form.title} onChange={(e) => setForm((c) => ({ ...c, title: e.target.value }))} placeholder="Title *" className="!h-7 flex-1 !text-[10px]" />
                              <input value={form.message} onChange={(e) => setForm((c) => ({ ...c, message: e.target.value }))} placeholder="Body" className="!h-7 flex-1 !text-[10px]" />
                              <select value={form.urgency} onChange={(e) => setForm((c) => ({ ...c, urgency: e.target.value }))} className="!h-7 !text-[10px] !py-0">
                                <option value="">Urgency</option>
                                <option value="low">Low</option>
                                <option value="normal">Normal</option>
                                <option value="critical">Critical</option>
                              </select>
                            </div>
                          ) : (
                            <div className="flex flex-wrap gap-1.5">
                              <input value={form.command} onChange={(e) => setForm((c) => ({ ...c, command: e.target.value }))} placeholder={step.type === "open_url" ? "URL" : step.type === "hotkey" ? "Shortcut" : "Command"} className="!h-7 flex-1 !text-[10px]" />
                              {step.type === "command" && (
                                <>
                                  <input value={form.workingDirectory} onChange={(e) => setForm((c) => ({ ...c, workingDirectory: e.target.value }))} placeholder="Working dir" className="!h-7 flex-1 !text-[10px]" />
                                  <select value={form.executionMode} onChange={(e) => setForm((c) => ({ ...c, executionMode: e.target.value as "argv" | "detached" }))} className="!h-7 !text-[10px] !py-0">
                                    <option value="argv">argv</option>
                                    <option value="detached">detached</option>
                                  </select>
                                </>
                              )}
                            </div>
                          )}
                          <div className="flex gap-1">
                            <button type="button" className="!h-7 !px-2 !py-0 !text-[10px]" onClick={() => submitEdit(step)}>Save</button>
                            <button type="button" className="!h-7 !px-2 !py-0 !text-[10px]" onClick={() => setEditingStepKey(null)}>Cancel</button>
                          </div>
                        </div>
                      ) : (
                        <div className="grid grid-cols-[28px_minmax(0,1fr)_auto] items-center gap-2">
                          <div className="font-mono text-[11px] text-white/40">{index + 1}</div>
                          <div className="min-w-0">
                            <div className="truncate text-xs text-white/85">{stepSummary(step)}</div>
                            <div className="mt-0.5 flex flex-wrap gap-1">
                              <StepTypeBadge step={step} />
                              {!step.enabled && (
                                <span className="rounded bg-amber-300/[0.08] !px-1.5 !py-px text-[9.5px] text-amber-200/70">
                                  disabled
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-0.5">
                            <button type="button" className="!h-7 !w-7 !rounded !p-0 !text-[11px] text-white/40 hover:text-white/70" disabled={index === 0} onClick={() => onMoveStep?.(step.bindingId, step.bindingActionId, "up")}>↑</button>
                            <button type="button" className="!h-7 !w-7 !rounded !p-0 !text-[11px] text-white/40 hover:text-white/70" disabled={index === group.steps.length - 1} onClick={() => onMoveStep?.(step.bindingId, step.bindingActionId, "down")}>↓</button>
                            <button type="button" className="!h-7 !rounded !px-1.5 !py-0 !text-[10px]" onClick={() => onToggleStep?.(step.bindingId, step.bindingActionId, !step.enabled)}>
                              {step.enabled ? "On" : "Off"}
                            </button>
                            <button type="button" className="!h-7 !rounded !px-1.5 !py-0 !text-[10px]" onClick={() => startEdit(step)}>Edit</button>
                            <button type="button" className="!h-7 !rounded !px-1.5 !py-0 !text-[10px] text-rose-300/70" onClick={() => onDeleteStep?.(step.bindingId, step.bindingActionId)}>Del</button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
