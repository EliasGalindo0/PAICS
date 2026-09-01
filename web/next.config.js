/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Upload de PDF da KB (livros) pode levar vários minutos.
  experimental: {
    proxyTimeout: 600000,
  },
  // Monolith (Docker/Railway): Next.js proxy /api → FastAPI em 127.0.0.1:8000.
  // Serviços separados: DISABLE_API_REWRITE=1 e NEXT_PUBLIC_API_URL na build apontando para a API.
  async rewrites() {
    if (process.env.DISABLE_API_REWRITE === "1") return [];
    const apiOrigin = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";
    return [
      { source: "/api/:path*", destination: `${apiOrigin}/api/:path*` },
    ];
  },
};

module.exports = nextConfig;
