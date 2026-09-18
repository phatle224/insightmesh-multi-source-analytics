import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["frontend", "127.0.0.1", "host.docker.internal"],
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
