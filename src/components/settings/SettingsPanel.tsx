export function SettingsPanel() {
  return (
    <section className="rounded-md border border-white/10 bg-white/[0.03] p-4">
      <h2 className="text-base font-semibold text-white">Settings</h2>
      <p className="mt-1 text-xs text-white/45">Placeholder for automation, matching, execution, and import/export controls.</p>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-md border border-white/10 bg-black/20 p-3">
          <div className="text-sm font-medium text-white">Automation safety</div>
          <div className="mt-1 text-xs text-white/45">Global armed state and per-binding require armed policy.</div>
        </div>
        <div className="rounded-md border border-white/10 bg-black/20 p-3">
          <div className="text-sm font-medium text-white">Matching mode</div>
          <div className="mt-1 text-xs text-white/45">Legacy, v2, or dual matching during migration.</div>
        </div>
      </div>
    </section>
  );
}

