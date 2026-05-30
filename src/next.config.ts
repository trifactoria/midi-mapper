import type { NextConfig } from "next";

// When MIDI_MAPPER_PACKAGE_BUILD=true, produce a static export suitable for
// bundling into the Tauri AppImage/deb via frontendDist.
// Normal dev and check.sh builds are unaffected (no output override, next start works).
const isPackageBuild = process.env.MIDI_MAPPER_PACKAGE_BUILD === "true";

const nextConfig: NextConfig = {
  ...(isPackageBuild && {
    output: "export",
    // Write static files directly to the Tauri frontendDist directory.
    distDir: "../src-tauri/frontend-dist",
    // next/image optimization requires a server; use passthrough for static builds.
    images: { unoptimized: true },
    // Trailing slashes so /v2/ maps to v2/index.html in Tauri's file protocol.
    trailingSlash: true,
  }),
};

export default nextConfig;
