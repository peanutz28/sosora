import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  devIndicators: false,
  distDir: process.env.SOSORA_NEXT_DIST_DIR || ".next",
};

export default nextConfig;
