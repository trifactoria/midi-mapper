"use client";

import { useEffect, useRef } from "react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
};

export function Modal({ isOpen, onClose, title, children }: Props) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      ref={overlayRef}
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.8)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "20px",
      }}
    >
      <div
        style={{
          background: "linear-gradient(135deg, #1a1a1a, #0f0f0f)",
          border: "2px solid rgba(0, 212, 255, 0.3)",
          borderRadius: "12px",
          boxShadow: "0 0 40px rgba(0, 212, 255, 0.2), 0 20px 60px rgba(0, 0, 0, 0.5)",
          maxWidth: "500px",
          width: "100%",
          animation: "modalSlideIn 0.2s ease-out",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <h2
            style={{
              margin: 0,
              fontSize: "18px",
              fontWeight: 600,
              color: "var(--accent)",
              textShadow: "0 0 10px rgba(0, 212, 255, 0.3)",
            }}
          >
            {title}
          </h2>
          <button
            onClick={onClose}
            className="btn"
            style={{
              padding: "6px 12px",
              fontSize: "20px",
              lineHeight: 1,
              opacity: 0.7,
            }}
            title="Close (Esc)"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: "24px" }}>{children}</div>
      </div>

      <style jsx>{`
        @keyframes modalSlideIn {
          from {
            opacity: 0;
            transform: translateY(-20px) scale(0.95);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
      `}</style>
    </div>
  );
}
