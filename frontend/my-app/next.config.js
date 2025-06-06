/** @type {import('next').NextConfig} */
const nextConfig = {
  /* config options here */

  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*', // Proxy to Backend
      },
    ];
  },

  // Other configurations might follow
};

module.exports = nextConfig; 