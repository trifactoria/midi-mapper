"use client";

import { useEffect } from "react";

type Props = {
  open: boolean;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  open,
  message,
  confirmLabel = "Confirm",
  onConfirm,
  onCancel,
}: Props) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onCancel}
    >
      <div
        className="w-64 rounded-lg border border-white/12 bg-zinc-900 p-4 shadow-[0_8px_32px_rgba(0,0,0,0.6)]"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-[12.5px] leading-relaxed text-white/80">{message}</p>
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded border border-white/10 !px-3 !py-1.5 !text-[11.5px] text-white/65 hover:text-white/90"
            style={{ background: "rgba(255,255,255,0.04)" }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded border border-rose-400/25 !px-3 !py-1.5 !text-[11.5px] text-rose-200 hover:text-rose-100"
            style={{ background: "rgba(244,63,94,0.10)" }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
