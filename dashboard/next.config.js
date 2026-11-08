/** @type {import('next').NextConfig} */
// The Pages demo is a static export: no server, no runtime. The normal build stays
// server-capable, so the switch is opt-in per build.
const staticExport = process.env.NEXT_STATIC_EXPORT === "1";
const basePath = process.env.NEXT_BASE_PATH || "";

const nextConfig = staticExport
  ? {
      // Inlined into the bundle so a page can tell export mode from a connected build.
      env: { NEXT_STATIC_EXPORT: "1" },
      output: "export",
      trailingSlash: true,
      images: { unoptimized: true },
      basePath: basePath || undefined,
      assetPrefix: basePath || undefined,
    }
  : { env: { NEXT_STATIC_EXPORT: "" } };

module.exports = nextConfig;
