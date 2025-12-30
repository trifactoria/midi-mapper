// app/layout.tsx
import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

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
          geistSans.variable,
          geistMono.variable,
          "antialiased",
        ].join(" ")}
      >
        {/* App shell */}
        <div className="min-h-screen">
          <header className="sticky top-0 z-50 border-b border-white/10 bg-black/70 backdrop-blur">
            <div className="mx-auto flex max-w-[1400px] items-center justify-between px-4 py-3">
              <div className="flex items-baseline gap-3">
                <div className="text-sm font-semibold tracking-wide">
                  MIDI Mapper
                </div>
                <div className="text-xs text-white/55">
                  Setup Mode
                </div>
              </div>
              <div className="text-xs text-white/45">
                Local-first · No cloud
              </div>
            </div>
          </header>

          <main className="mx-auto w-full max-w-[1400px] px-4 py-4">
            {children}
          </main>

          <footer className="mx-auto w-full max-w-[1400px] px-4 pb-6 pt-2 text-xs text-white/35">
            MIDI Mapper · map MIDI → commands
          </footer>
        </div>
      </body>
    </html>
  );
}
