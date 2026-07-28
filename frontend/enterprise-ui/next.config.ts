import type { NextConfig } from "next";

const backendUrl =
  process.env.CTV_BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "127.0.0.1",
    "localhost",
    "192.168.31.42",
  ],

  async rewrites() {
    return [
      {
        source: "/ctv-api/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;