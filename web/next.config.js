/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Em DEV, proxy para a FastAPI local. Em PROD (Railway), use NEXT_PUBLIC_API_URL no browser.
  async rewrites() {
    if (process.env.NODE_ENV === "production") return [];
    return [
      { source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" },
    ];
  },
};

module.exports = nextConfig;
