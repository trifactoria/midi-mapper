// app/layout.tsx
import type { Metadata, Viewport } from "next";
import { Header } from "../components/Header";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "MIDI Mapper",
    template: "%s · MIDI Mapper",
  },
  description:
    "Map MIDI input to local commands. Context-aware bindings (port/channel/bank/program), fast setup UI, and headless execution.",
  applicationName: "MIDI Mapper",
  authors: [{ name: "MIDI Mapper" }],
  generator: "Next.js",
  referrer: "strict-origin-when-cross-origin",
  category: "productivity",
  keywords: [
    "midi",
    "macro pad",
    "stream deck",
    "linux",
    "awesomewm",
    "keyboard shortcuts",
    "automation",
  ],
  icons: {
    icon: "/favicon.ico",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0b0b0b",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full bg-black text-white">
      <body
        className={[
          "min-h-full",
          "antialiased",
        ].join(" ")}
      >
        {/* App shell */}
        <div className="min-h-screen">
          <Header />

          <main className="mx-auto w-full max-w-[1400px] px-4 py-4">
            {children}
          </main>

          <footer className="mx-auto w-full max-w-[1400px] px-4 pb-6 pt-2 text-center text-xs text-white/35">
            <div>
              © {new Date().getFullYear()}{" "}
              <a
                href="https://github.com/trifactoria"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "inherit", textDecoration: "underline" }}
              >
                TriFactoria
              </a>
              {" · "}
              <a
                href="https://github.com/trifactoria/midi-mapper"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "inherit", textDecoration: "underline" }}
              >
                GitHub
              </a>
              {" · "}
              <a
                href="https://github.com/sponsors/trifactoria"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "inherit", textDecoration: "underline" }}
              >
                Sponsor
              </a>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
