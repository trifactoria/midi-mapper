"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";

export function Header() {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-black/70 backdrop-blur">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          {/* Logo button */}
          <div style={{ position: "relative" }}>
            <button
              onClick={() => setShowMenu(!showMenu)}
              style={{
                padding: 4,
                border: "none",
                background: "transparent",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                borderRadius: 6,
                transition: "background 0.2s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.08)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              title="Menu"
            >
              <Image
                src="/logo.png"
                alt="MIDI Mapper"
                width={24}
                height={24}
                style={{ width: 24, height: 24, display: "block" }}
              />
            </button>

            {/* Popover menu */}
            {showMenu && (
              <>
                <div
                  style={{
                    position: "fixed",
                    inset: 0,
                    zIndex: 40,
                  }}
                  onClick={() => setShowMenu(false)}
                />
                <div
                  style={{
                    position: "absolute",
                    top: "calc(100% + 8px)",
                    left: 0,
                    background: "rgba(20, 20, 20, 0.95)",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: 10,
                    padding: "8px 0",
                    minWidth: 160,
                    boxShadow: "0 8px 24px rgba(0, 0, 0, 0.6)",
                    backdropFilter: "blur(10px)",
                    zIndex: 50,
                  }}
                >
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      alert("MIDI Mapper runs locally. Select a MIDI context, choose a note/control, then create a command binding. Keep command execution limited to trusted local workflows.");
                      setShowMenu(false);
                    }}
                    style={{
                      display: "block",
                      padding: "8px 16px",
                      fontSize: 14,
                      color: "#ededed",
                      textDecoration: "none",
                      transition: "background 0.15s",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0, 212, 255, 0.1)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    Help
                  </a>
                  <div style={{ height: 1, background: "rgba(255, 255, 255, 0.1)", margin: "4px 0" }} />
                  <a
                    href="https://github.com/trifactoria/midi-mapper"
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: "block",
                      padding: "8px 16px",
                      fontSize: 14,
                      color: "#ededed",
                      textDecoration: "none",
                      transition: "background 0.15s",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0, 212, 255, 0.1)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    GitHub
                  </a>
                  <a
                    href="https://github.com/sponsors/trifactoria"
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: "block",
                      padding: "8px 16px",
                      fontSize: 14,
                      color: "#ededed",
                      textDecoration: "none",
                      transition: "background 0.15s",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0, 212, 255, 0.1)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    Sponsor
                  </a>
                  <div style={{ height: 1, background: "rgba(255, 255, 255, 0.1)", margin: "4px 0" }} />
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      alert("MIDI Mapper\n\nA Stream Deck-style MIDI macro pad for Linux.\n\n© 2025 TriFactoria");
                      setShowMenu(false);
                    }}
                    style={{
                      display: "block",
                      padding: "8px 16px",
                      fontSize: 14,
                      color: "#ededed",
                      textDecoration: "none",
                      transition: "background 0.15s",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0, 212, 255, 0.1)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    About
                  </a>
                </div>
              </>
            )}
          </div>

          <Link
            href="/"
            className="text-sm font-semibold tracking-wide"
            style={{ color: "inherit", textDecoration: "none" }}
          >
            MIDI Mapper
          </Link>
        </div>
        <div className="text-xs text-white/45">
          Local-first · No cloud
        </div>
      </div>
    </header>
  );
}
