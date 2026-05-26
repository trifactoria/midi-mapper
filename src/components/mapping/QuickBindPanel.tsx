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

function Toggle({ on, label }: { on: boolean; label: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
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

export function QuickBindPanel() {
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
            <select className="w-full !text-[11.5px]" defaultValue="note">
              <option value="note">Note</option>
              <option value="cc">CC</option>
              <option value="pc">PC</option>
            </select>
          </label>
          <label className="block">
            <FieldLabel>Channel</FieldLabel>
            <select className="w-full !text-[11.5px]" defaultValue="1">
              {Array.from({ length: 16 }, (_, i) => (
                <option key={i + 1}>{i + 1}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <FieldLabel>Note</FieldLabel>
            <input className="w-full font-mono !text-[11.5px]" defaultValue="C4 (60)" readOnly />
          </label>
        </div>

        <div className="mt-2 grid grid-cols-[1fr_auto] items-end gap-1.5">
          <div className="grid grid-cols-2 gap-1.5">
            <label className="block">
              <FieldLabel>Velocity Min</FieldLabel>
              <input className="w-full font-mono !text-[11.5px]" defaultValue="64" />
            </label>
            <label className="block">
              <FieldLabel>Velocity Max</FieldLabel>
              <input className="w-full font-mono !text-[11.5px]" defaultValue="127" />
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
            <select className="w-full !text-[11.5px]" defaultValue="command">
              <option value="command">Command</option>
              <option value="script">Script</option>
              <option value="osc">OSC</option>
            </select>
          </label>
          <label className="block">
            <FieldLabel>Command</FieldLabel>
            <input className="w-full font-mono !text-[11.5px]" defaultValue="code" readOnly />
          </label>
        </div>

        <label className="mt-1.5 block">
          <FieldLabel optional>Arguments</FieldLabel>
          <input className="w-full font-mono !text-[11.5px]" defaultValue="." readOnly />
        </label>

        <label className="mt-1.5 block">
          <FieldLabel optional>Working Directory</FieldLabel>
          <input className="w-full font-mono !text-[11.5px]" defaultValue="~/projects" readOnly />
        </label>

        <button
          type="button"
          className="mt-2 inline-flex !h-7 items-center gap-1.5 rounded-md border border-purple-300/30 bg-purple-300/[0.10] !px-2.5 !text-[10.5px] uppercase tracking-[0.10em] font-semibold text-purple-100 hover:bg-purple-300/[0.16]"
        >
          <span aria-hidden>▶</span> Test Action
        </button>
      </section>

      {/* Binding Options */}
      <section className="rounded-md border border-white/8 bg-white/[0.014] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.018),inset_0_0_24px_rgba(0,0,0,0.18)]">
        <div className="mb-1.5">
          <SectionLabel>Binding Options</SectionLabel>
        </div>

        <div className="space-y-1.5">
          <Toggle on label="Active" />
          <Toggle on={false} label="Require Armed" />
        </div>

        <div className="mt-2 grid grid-cols-2 gap-1.5">
          <label className="block">
            <FieldLabel>Cooldown (ms)</FieldLabel>
            <input className="w-full font-mono !text-[11.5px]" defaultValue="250" />
          </label>
          <label className="block">
            <FieldLabel>Debounce (ms)</FieldLabel>
            <input className="w-full font-mono !text-[11.5px]" defaultValue="20" />
          </label>
        </div>

        <label className="mt-2 block">
          <FieldLabel optional>Notes</FieldLabel>
          <textarea
            className="block w-full font-mono !text-[11.5px]"
            rows={2}
            placeholder="Optional notes about this binding..."
          />
        </label>

        <button
          type="button"
          className="btn-primary mt-2 w-full rounded-md !text-[11.5px] !py-1.5"
        >
          + Create Binding
        </button>
      </section>
    </div>
  );
}
