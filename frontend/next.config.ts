import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow access via local network IP (company laptop dev setup)
  allowedDevOrigins: ["10.158.200.144"],
};

export default nextConfig;
