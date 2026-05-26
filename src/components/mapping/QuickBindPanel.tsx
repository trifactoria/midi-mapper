import { useEffect, useMemo, useState } from "react";
import type { BackendActionRunResult, BackendBindingCreatePayload } from "../v2/api";
import type { V2BindingSummary } from "../v2/types";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-200/80">
      {children}
    </h3>
  );
}

function FieldLabel({ children, optional }: { children: React.ReactNode; optional?: boolean }) {
  return (
    <span className="mb-0.5 block text-[10px] uppercase tracking-[0.12em] text-white/45">
      {children}
      {optional && <span className="text-white/25"> (optional)</span>}
    </span>
  );
}

function Toggle({ on, label, onClick }: { on: boolean; label: string; onClick?: () => void }) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") onClick?.();
      }}
      className="flex items-center justify-between gap-3"
    >
      <span className="text-[11.5px] text-white/80">{label}</span>
      <span
        className={[
          "relative inline-flex h-4 w-7 shrink-0 rounded-full transition",
          on ? "bg-emerald-400/80 shadow-[0_0_10px_rgba(52,211,153,0.45)]" : "bg-white/15",
        ].join(" ")}
        aria-hidden
      >
        <span
          className={[
            "absolute top-0.5 h-3 w-3 rounded-full bg-white transition",
            on ? "left-[14px]" : "left-0.5",
          ].join(" ")}
        />
      </span>
    </div>
  );
}

type Props = {
  selectedBinding?: V2BindingSummary | null;
  canMutateBindings: boolean;
  onCreateBinding: (payload: BackendBindingCreatePayload) => Promise<V2BindingSummary>;
  onDryRunAction: (actionId: string) => Promise<BackendActionRunResult>;
  onTestAction: (actionId: string) => Promise<BackendActionRunResult>;
  onBindingCreated?: (binding: V2BindingSummary) => void;
};

function numberFromText(value: string): number | undefined {
  const match = value.match(/\d+/);
  if (!match) return undefined;
  const parsed = Number(match[0]);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function boundedMidiValue(value: string): number | undefined {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return undefined;
  return Math.max(0, Math.min(127, Math.round(parsed)));
}

function resultText(result: BackendActionRunResult | null): string | null {
  if (!result) return null;
  if (result.summary) return `Dry run: ${result.summary}`;
  if (result.error) return `Error: ${result.error}`;
  if (result.stderr || result.stderr_preview) return `stderr: ${result.stderr ?? result.stderr_preview}`;
  if (result.stdout || result.stdout_preview) return `stdout: ${result.stdout ?? result.stdout_preview}`;
  if (result.ok !== undefined) return result.ok ? "Action test succeeded" : "Action test failed";
  return null;
}

export function QuickBindPanel({
  selectedBinding,
  canMutateBindings,
  onCreateBinding,
  onDryRunAction,
  onTestAction,
  onBindingCreated,
}: Props) {
  const [eventType, setEventType] = useState<"note" | "cc">("note");
  const [channel, setChannel] = useState("1");
  const [note, setNote] = useState("60");
  const [controller, setController] = useState("21");
  const [velocityMin, setVelocityMin] = useState("64");
  const [velocityMax, setVelocityMax] = useState("127");
  const [valueMin, setValueMin] = useState("0");
  const [valueMax, setValueMax] = useState("127");
  const [command, setCommand] = useState("echo");
  const [args, setArgs] = useState("hello");
  const [workingDirectory, setWorkingDirectory] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [requireArmed, setRequireArmed] = useState(true);
  const [cooldownMs, setCooldownMs] = useState("250");
  const [debounceMs, setDebounceMs] = useState("20");
  const [notes, setNotes] = useState("");
  const [lastActionId, setLastActionId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<BackendActionRunResult | null>(null);

  useEffect(() => {
    if (!selectedBinding) return;
    setEventType(selectedBinding.kind);
    setChannel(String((selectedBinding.channel ?? 0) + 1));
    if (selectedBinding.kind === "cc") {
      setController(String(selectedBinding.controller ?? numberFromText(selectedBinding.triggerLabel) ?? 21));
      setValueMin(String(selectedBinding.valueMin ?? 0));
      setValueMax(String(selectedBinding.valueMax ?? 127));
    } else {
      setNote(String(selectedBinding.note ?? numberFromText(selectedBinding.triggerLabel) ?? 60));
      setVelocityMin(String(selectedBinding.velocityMin ?? 0));
      setVelocityMax(String(selectedBinding.velocityMax ?? 127));
    }
    setCommand(selectedBinding.command || selectedBinding.actionLabel || "echo");
    setArgs("");
    setEnabled(selectedBinding.enabled);
    setRequireArmed(selectedBinding.requireArmed);
    setLastActionId(selectedBinding.actionId ?? null);
    setMessage(null);
    setRunResult(null);
  }, [selectedBinding]);

  const actionId = selectedBinding?.actionId ?? lastActionId;
  const commandLine = useMemo(() => [command.trim(), args.trim()].filter(Boolean).join(" "), [args, command]);

  async function createBinding() {
    setMessage(null);
    setRunResult(null);
    if (!canMutateBindings) {
      setMessage("Mock fallback: start backend and seed demo data to create real bindings");
      return;
    }
    if (!commandLine) {
      setMessage("Command is required");
      return;
    }

    const trigger =
      eventType === "cc"
        ? {
            event_type: "control_change" as const,
            channel: Number(channel),
            controller: boundedMidiValue(controller),
            value_min: boundedMidiValue(valueMin),
            value_max: boundedMidiValue(valueMax),
          }
        : {
            event_type: "note_on" as const,
            channel: Number(channel),
            note: boundedMidiValue(note),
            velocity_min: boundedMidiValue(velocityMin),
            velocity_max: boundedMidiValue(velocityMax),
          };

    try {
      const created = await onCreateBinding({
        trigger,
        action: {
          type: "command",
          label: command.trim() || commandLine,
          command: commandLine,
          execution_mode: "argv",
        },
        enabled: enabled ? 1 : 0,
        require_armed: requireArmed ? 1 : 0,
        cooldown_ms: Number(cooldownMs) || 200,
        notes,
        display_label: command.trim() || commandLine,
      });
      setLastActionId(created.actionId ?? null);
      setMessage("Binding created");
      onBindingCreated?.(created);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Create binding failed");
    }
  }

  async function dryRunAction() {
    setMessage(null);
    if (!actionId) {
      setMessage("Mock fallback: select or create a real backend binding first");
      return;
    }
    try {
      const result = await onDryRunAction(actionId);
      setRunResult(result);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Dry run failed");
    }
  }

  async function testAction() {
    setMessage(null);
    if (!actionId) {
      setMessage("Mock fallback: select or create a real backend binding first");
      return;
    }
    try {
      const result = await onTestAction(actionId);
      setRunResult(result);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Test action failed");
    }
  }

  return (
    <div className="space-y-2">
      {/* Quick Bind */}
      <section className="rounded-md border border-white/8 bg-white/[0.014] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.018),inset_0_0_24px_rgba(0,0,0,0.18)]">
        <div className="mb-1.5 flex items-center justify-between">
          <SectionLabel>Quick Bind</SectionLabel>
          <span className="rounded border border-cyan-300/25 bg-cyan-300/[0.06] !px-1.5 !py-px text-[9.5px] uppercase tracking-[0.14em] text-cyan-100">
            Capture
          </span>
        </div>

        <div className="grid grid-cols-3 gap-1.5">
          <label className="block">
            <FieldLabel>Event Type</FieldLabel>
            <select className="w-full !text-[11.5px]" value={eventType} onChange={(event) => setEventType(event.target.value as "note" | "cc")}>
              <option value="note">Note</option>
              <option value="cc">CC</option>
            </select>
          </label>
          <label className="block">
            <FieldLabel>Channel</FieldLabel>
            <select className="w-full !text-[11.5px]" value={channel} onChange={(event) => setChannel(event.target.value)}>
              {Array.from({ length: 16 }, (_, i) => (
                <option key={i + 1}>{i + 1}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <FieldLabel>{eventType === "cc" ? "Controller" : "Note"}</FieldLabel>
            <input className="w-full font-mono !text-[11.5px]" value={eventType === "cc" ? controller : note} onChange={(event) => eventType === "cc" ? setController(event.target.value) : setNote(event.target.value)} />
          </label>
        </div>

        <div className="mt-2 grid grid-cols-[1fr_auto] items-end gap-1.5">
          <div className="grid grid-cols-2 gap-1.5">
            <label className="block">
              <FieldLabel>Velocity Min</FieldLabel>
              <input className="w-full font-mono !text-[11.5px]" value={eventType === "cc" ? valueMin : velocityMin} onChange={(event) => eventType === "cc" ? setValueMin(event.target.value) : setVelocityMin(event.target.value)} />
            </label>
            <label className="block">
              <FieldLabel>Velocity Max</FieldLabel>
              <input className="w-full font-mono !text-[11.5px]" value={eventType === "cc" ? valueMax : velocityMax} onChange={(event) => eventType === "cc" ? setValueMax(event.target.value) : setVelocityMax(event.target.value)} />
            </label>
          </div>
          <button
            type="button"
            className="!h-7 shrink-0 rounded-md border border-cyan-300/30 bg-cyan-300/[0.10] !px-2.5 !text-[10.5px] uppercase tracking-[0.10em] font-semibold text-cyan-100 hover:bg-cyan-300/[0.16]"
          >
            Capture Next
          </button>
        </div>
      </section>

      {/* Action Preview */}
      <section className="rounded-md border border-white/8 bg-white/[0.014] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.018),inset_0_0_24px_rgba(0,0,0,0.18)]">
        <div className="mb-1.5">
          <SectionLabel>Action Preview</SectionLabel>
        </div>

        <div className="grid grid-cols-[1fr_2fr] gap-1.5">
          <label className="block">
            <FieldLabel>Type</FieldLabel>
            <select className="w-full !text-[11.5px]" value="command" onChange={() => undefined}>
              <option value="command">Command</option>
            </select>
          </label>
          <label className="block">
            <FieldLabel>Command</FieldLabel>
            <input className="w-full font-mono !text-[11.5px]" value={command} onChange={(event) => setCommand(event.target.value)} />
          </label>
        </div>

        <label className="mt-1.5 block">
          <FieldLabel optional>Arguments</FieldLabel>
          <input className="w-full font-mono !text-[11.5px]" value={args} onChange={(event) => setArgs(event.target.value)} />
        </label>

        <label className="mt-1.5 block">
          <FieldLabel optional>Working Directory</FieldLabel>
          <input className="w-full font-mono !text-[11.5px]" value={workingDirectory} onChange={(event) => setWorkingDirectory(event.target.value)} />
        </label>

        <div className="mt-2 flex gap-1.5">
          <button
            type="button"
            onClick={() => void testAction()}
            className="inline-flex !h-7 items-center gap-1.5 rounded-md border border-purple-300/30 bg-purple-300/[0.10] !px-2.5 !text-[10.5px] uppercase tracking-[0.10em] font-semibold text-purple-100 hover:bg-purple-300/[0.16]"
          >
            <span aria-hidden>▶</span> Test Action
          </button>
          <button
            type="button"
            onClick={() => void dryRunAction()}
            className="inline-flex !h-7 items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.03] !px-2.5 !text-[10.5px] uppercase tracking-[0.10em] font-semibold text-white/75 hover:bg-white/[0.06]"
          >
            Dry Run
          </button>
        </div>
        {resultText(runResult) && <div className="mt-1.5 truncate font-mono text-[10.5px] text-white/55">{resultText(runResult)}</div>}
      </section>

      {/* Binding Options */}
      <section className="rounded-md border border-white/8 bg-white/[0.014] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.018),inset_0_0_24px_rgba(0,0,0,0.18)]">
        <div className="mb-1.5">
          <SectionLabel>Binding Options</SectionLabel>
        </div>

        <div className="space-y-1.5">
          <Toggle on={enabled} label="Active" onClick={() => setEnabled((value) => !value)} />
          <Toggle on={requireArmed} label="Require Armed" onClick={() => setRequireArmed((value) => !value)} />
        </div>

        <div className="mt-2 grid grid-cols-2 gap-1.5">
          <label className="block">
            <FieldLabel>Cooldown (ms)</FieldLabel>
            <input className="w-full font-mono !text-[11.5px]" value={cooldownMs} onChange={(event) => setCooldownMs(event.target.value)} />
          </label>
          <label className="block">
            <FieldLabel>Debounce (ms)</FieldLabel>
            <input className="w-full font-mono !text-[11.5px]" value={debounceMs} onChange={(event) => setDebounceMs(event.target.value)} />
          </label>
        </div>

        <label className="mt-2 block">
          <FieldLabel optional>Notes</FieldLabel>
          <textarea
            className="block w-full font-mono !text-[11.5px]"
            rows={2}
            placeholder="Optional notes about this binding..."
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
        </label>

        <button
          type="button"
          onClick={() => void createBinding()}
          className="btn-primary mt-2 w-full rounded-md !text-[11.5px] !py-1.5"
        >
          + Create Binding
        </button>
        {message && <div className="mt-1.5 truncate font-mono text-[10.5px] text-white/55">{message}</div>}
      </section>
    </div>
  );
}
