/** VIXOR — Next.js 14 config */

const nextConfig = {
  reactStrictMode: true,
  experimental: {
    serverActions: true,
  },
  async rewrites() {
    return []
  },
}

module.exports = nextConfig
