import type { NextConfig } from "next";
import path from "path";

// Pin Turbopack workspace root to the frontend directory.
// Without this, Turbopack walks up to the repo root (which has a sibling
// package.json but no node_modules) and fails to resolve tailwindcss.
// `path.resolve(".")` = process.cwd(), which is `frontend/` because
// `next dev` is always launched from this folder.
const nextConfig: NextConfig = {
  // Allow access via local network IP (company laptop dev setup)
  allowedDevOrigins: ["10.158.200.144"],

  turbopack: {
    root: path.resolve("."),
  },
};

export default nextConfig;
