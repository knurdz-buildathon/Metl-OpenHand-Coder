/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@metl/shared", "@metl/browser-agent", "@metl/cursor-sdk-plugin"],
  experimental: {
    serverComponentsExternalPackages: ["playwright", "@playwright/test"],
  },
  async rewrites() {
    if (process.env.NODE_ENV === "development") {
      return [
        {
          source: "/api/:path*",
          destination: "http://localhost:8000/api/:path*",
        },
      ];
    }
    return [];
  },
};

module.exports = nextConfig;