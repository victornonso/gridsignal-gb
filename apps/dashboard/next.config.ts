import type { NextConfig } from "next";
const config: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.API_INTERNAL_URL || "http://127.0.0.1:8001"}/api/v1/:path*`,
      },
    ];
  },
};
export default config;
