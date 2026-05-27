"use client";

import { useMemo, useState } from "react";
import type { V2ActionStep, V2BindingSummary } from "../v2/types";

type CommandPayload = {
  label?: string;
  command: string;
  workingDirectory?: string;
  executionMode?: "argv" | "detached";
  timeoutMs?: number;
};

type StepPatch = Partial<CommandPayload> & { durationMs?: number };

type Props = {
  bindings: V2BindingSummary[];
  onAddDelayStep?: (bindingId: string) => void;
  onAddCommandStep?: (bindingId: string, payload: CommandPayload) => void;
  onUpdateStep?: (bindingId: string, bindingActionId: string, patch: StepPatch) => void;
  onDeleteStep?: (bindingId: string, bindingActionId: string) => void;
  onMoveStep?: (bindingId: string, bindingActionId: string, direction: "up" | "down") => void;
  onToggleStep?: (bindingId: string, bindingActionId: string, enabled: boolean) => void;
};

type TriggerGroup = {
  key: string;
  label: string;
  bindings: V2BindingSummary[];
  steps: V2ActionStep[];
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
  return step.command || step.label || "Command";
}

function commandWithArgs(command: string, args: string): string {
  return [command.trim(), args.trim()].filter(Boolean).join(" ");
}

export function ActionsPanel({
  bindings,
  onAddDelayStep,
  onAddCommandStep,
  onUpdateStep,
  onDeleteStep,
  onMoveStep,
  onToggleStep,
}: Props) {
  const [addGroupKey, setAddGroupKey] = useState<string | null>(null);
  const [editingStepKey, setEditingStepKey] = useState<string | null>(null);
  const [form, setForm] = useState({
    label: "",
    command: "",
    args: "",
    workingDirectory: "",
    executionMode: "argv" as "argv" | "detached",
    timeoutMs: "",
    durationMs: "3000",
  });

  const groups = useMemo<TriggerGroup[]>(() => {
    const byKey = new Map<string, TriggerGroup>();
    for (const binding of bindings) {
      const key = triggerKey(binding);
      const existing = byKey.get(key);
      const group =
        existing ??
        {
          key,
          label: `${binding.triggerLabel}${binding.triggerCondition ? ` · ${binding.triggerCondition}` : ""}`,
          bindings: [],
          steps: [],
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
    setForm({
      label: "",
      command: "",
      args: "",
      workingDirectory: "",
      executionMode: "argv",
      timeoutMs: "",
      durationMs: "3000",
    });
  };

  const startEdit = (step: V2ActionStep) => {
    setEditingStepKey(step.bindingActionId);
    setAddGroupKey(null);
    setForm({
      label: step.label,
      command: step.command ?? "",
      args: "",
      workingDirectory: step.workingDirectory ?? "",
      executionMode: step.executionMode === "detached" ? "detached" : "argv",
      timeoutMs: step.timeoutMs == null ? "" : String(step.timeoutMs),
      durationMs: String(step.durationMs ?? 3000),
    });
  };

  const submitCommand = (bindingId: string) => {
    const command = commandWithArgs(form.command, form.args);
    if (!command) return;
    onAddCommandStep?.(bindingId, {
      label: form.label,
      command,
      workingDirectory: form.workingDirectory || undefined,
      executionMode: form.executionMode,
      timeoutMs: form.timeoutMs ? Number(form.timeoutMs) : undefined,
    });
    setAddGroupKey(null);
    resetForm();
  };

  const submitEdit = (step: V2ActionStep) => {
    const patch: StepPatch =
      step.type === "delay"
        ? { durationMs: Number(form.durationMs || 0), label: form.label }
        : {
            label: form.label,
            command: commandWithArgs(form.command, form.args),
            workingDirectory: form.workingDirectory || undefined,
            executionMode: form.executionMode,
            timeoutMs: form.timeoutMs ? Number(form.timeoutMs) : undefined,
          };
    onUpdateStep?.(step.bindingId, step.bindingActionId, patch);
    setEditingStepKey(null);
    resetForm();
  };

  return (
    <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-white">Actions</h2>
          <p className="text-xs text-white/45">Automation sequences grouped by trigger in the active layer.</p>
        </div>
        <div className="flex shrink-0 gap-1.5 font-mono text-[10px] text-white/45">
          <span className="rounded border border-white/10 bg-white/[0.04] px-1.5 py-px">{groups.length} triggers</span>
          <span className="rounded border border-white/10 bg-white/[0.04] px-1.5 py-px">{steps.length} steps</span>
          <span className="rounded border border-emerald-300/15 bg-emerald-300/[0.05] px-1.5 py-px">{enabledCount} enabled</span>
        </div>
      </div>

      {groups.length === 0 ? (
        <p className="text-[11px] text-white/30">No actions yet - add bindings from the Mapping tab.</p>
      ) : (
        <div className="grid gap-3">
          {groups.map((group) => {
            const targetBindingId = group.bindings[0]?.id;
            return (
              <div key={group.key} className="rounded-md border border-white/10 bg-black/20 p-3">
                <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-white">Trigger: {group.label}</div>
                    <div className="mt-0.5 text-[10px] uppercase tracking-[0.10em] text-white/40">
                      {group.bindings.length} binding row{group.bindings.length === 1 ? "" : "s"}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      className="!h-7 !rounded !px-2 !py-0 !text-[10px] text-cyan-100"
                      onClick={() => {
                        setAddGroupKey(addGroupKey === group.key ? null : group.key);
                        setEditingStepKey(null);
                        resetForm();
                      }}
                    >
                      + command
                    </button>
                    <button
                      type="button"
                      className="!h-7 !rounded !px-2 !py-0 !text-[10px] text-cyan-100"
                      onClick={() => targetBindingId && onAddDelayStep?.(targetBindingId)}
                    >
                      + wait
                    </button>
                  </div>
                </div>

                {addGroupKey === group.key && targetBindingId && (
                  <div className="mb-2 grid gap-2 rounded border border-cyan-300/15 bg-cyan-300/[0.04] p-2 md:grid-cols-[1fr_1.4fr_1.2fr_1fr_auto]">
                    <input value={form.label} onChange={(event) => setForm((current) => ({ ...current, label: event.target.value }))} placeholder="Label" />
                    <input value={form.command} onChange={(event) => setForm((current) => ({ ...current, command: event.target.value }))} placeholder="Command" />
                    <input value={form.args} onChange={(event) => setForm((current) => ({ ...current, args: event.target.value }))} placeholder="Arguments" />
                    <input value={form.workingDirectory} onChange={(event) => setForm((current) => ({ ...current, workingDirectory: event.target.value }))} placeholder="Working dir" />
                    <div className="flex gap-1">
                      <button type="button" className="!h-8 !px-2 !py-0 !text-[10px]" onClick={() => submitCommand(targetBindingId)}>Save</button>
                      <button type="button" className="!h-8 !px-2 !py-0 !text-[10px]" onClick={() => setAddGroupKey(null)}>Cancel</button>
                    </div>
                  </div>
                )}

                <div className="grid gap-1.5">
                  {group.steps.length === 0 && (
                    <div className="rounded border border-white/5 bg-white/[0.02] px-2 py-2 text-xs text-white/35">
                      No steps in this trigger sequence.
                    </div>
                  )}
                  {group.steps.map((step, index) => (
                    <div key={step.bindingActionId} className="rounded border border-white/10 bg-white/[0.03] p-2">
                      {editingStepKey === step.bindingActionId ? (
                        <div className="grid gap-2 md:grid-cols-[1fr_1.5fr_1fr_1fr_auto]">
                          <input value={form.label} onChange={(event) => setForm((current) => ({ ...current, label: event.target.value }))} placeholder="Label" />
                          {step.type === "delay" ? (
                            <input type="number" value={form.durationMs} onChange={(event) => setForm((current) => ({ ...current, durationMs: event.target.value }))} placeholder="Duration ms" />
                          ) : (
                            <input value={form.command} onChange={(event) => setForm((current) => ({ ...current, command: event.target.value }))} placeholder="Command" />
                          )}
                          {step.type === "command" && (
                            <>
                              <input value={form.workingDirectory} onChange={(event) => setForm((current) => ({ ...current, workingDirectory: event.target.value }))} placeholder="Working dir" />
                              <select value={form.executionMode} onChange={(event) => setForm((current) => ({ ...current, executionMode: event.target.value as "argv" | "detached" }))}>
                                <option value="argv">argv</option>
                                <option value="detached">detached</option>
                              </select>
                            </>
                          )}
                          <div className="flex gap-1">
                            <button type="button" className="!h-8 !px-2 !py-0 !text-[10px]" onClick={() => submitEdit(step)}>Save</button>
                            <button type="button" className="!h-8 !px-2 !py-0 !text-[10px]" onClick={() => setEditingStepKey(null)}>Cancel</button>
                          </div>
                        </div>
                      ) : (
                        <div className="grid grid-cols-[28px_minmax(0,1fr)_auto] items-center gap-2">
                          <div className="font-mono text-[11px] text-white/45">{index + 1}</div>
                          <div className="min-w-0">
                            <div className="truncate text-xs text-white/85">{stepSummary(step)}</div>
                            <div className="mt-0.5 flex flex-wrap gap-1.5 text-[10px] text-white/35">
                              <span className="rounded bg-white/[0.04] px-1.5 py-px">{step.type === "delay" ? "delay" : step.executionMode || "command"}</span>
                              {!step.enabled && <span className="rounded bg-amber-300/[0.08] px-1.5 py-px text-amber-200/70">disabled</span>}
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            <button type="button" className="!h-7 !w-7 !rounded !p-0 !text-[11px]" disabled={index === 0} onClick={() => onMoveStep?.(step.bindingId, step.bindingActionId, "up")}>^</button>
                            <button type="button" className="!h-7 !w-7 !rounded !p-0 !text-[11px]" disabled={index === group.steps.length - 1} onClick={() => onMoveStep?.(step.bindingId, step.bindingActionId, "down")}>v</button>
                            <button type="button" className="!h-7 !rounded !px-2 !py-0 !text-[10px]" onClick={() => onToggleStep?.(step.bindingId, step.bindingActionId, !step.enabled)}>{step.enabled ? "On" : "Off"}</button>
                            <button type="button" className="!h-7 !rounded !px-2 !py-0 !text-[10px]" onClick={() => startEdit(step)}>Edit</button>
                            <button type="button" className="!h-7 !rounded !px-2 !py-0 !text-[10px] text-rose-200" onClick={() => onDeleteStep?.(step.bindingId, step.bindingActionId)}>Delete</button>
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
