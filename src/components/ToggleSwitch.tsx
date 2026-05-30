// Shared toggle visual used across the app.
// ToggleTrack: aria-hidden track+thumb, embedded inside a parent button.
// ToggleSwitch: standalone interactive toggle (role="switch").

export function ToggleTrack({ on }: { on: boolean }) {
  return (
    <span
      className={[
        "relative inline-flex h-[18px] w-8 shrink-0 rounded-full border transition duration-150",
        on
          ? "border-emerald-300/40 bg-emerald-400/80 shadow-[0_0_10px_rgba(52,211,153,0.45)]"
          : "border-white/12 bg-white/[0.08]",
      ].join(" ")}
      aria-hidden
    >
      <span
        className={[
          "absolute top-0.5 h-3.5 w-3.5 rounded-full bg-white transition duration-150",
          on ? "left-[16px]" : "left-0.5",
        ].join(" ")}
      />
    </span>
  );
}

export function ToggleSwitch({
  on,
  onClick,
  disabled,
}: {
  on: boolean;
  onClick?: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      onClick={onClick}
      disabled={disabled}
      className={onClick && !disabled ? "cursor-pointer" : "cursor-default opacity-50"}
      style={{ background: "transparent", border: "none", padding: 0, minHeight: 0, lineHeight: 0 }}
    >
      <ToggleTrack on={on} />
    </button>
  );
}
