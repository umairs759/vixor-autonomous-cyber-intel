/** VIXOR — Next.js 14 config */

const nextConfig = {
  distDir: '.next-cors-verification',
  reactStrictMode: true,
  async rewrites() {
    return []
  },
}

module.exports = nextConfig
