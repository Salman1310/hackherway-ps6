import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

// Resolve this config file's own directory so Turbopack uses frontend/ as the
// project root regardless of where `next dev` is launched from. Without this,
// Turbopack walks up to the repo root (which has a sibling package.json)
// and fails to resolve `tailwindcss` because root has no node_modules.
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  // Allow access via local network IP (company laptop dev setup)
  allowedDevOrigins: ["10.158.200.144"],

  // Pin Turbopack workspace root to this folder (frontend/).
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
