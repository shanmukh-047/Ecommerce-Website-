/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: '127.0.0.1',
        port: '8000',
        pathname: '/media/**',
      },
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/media/**',
      },
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const backendTarget =
      process.env.BACKEND_INTERNAL_URL ||
      process.env.NEXT_PUBLIC_API_BASE_URL ||
      (process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000');

    if (!backendTarget) {
      return [];
    }

    const cleanBackend = backendTarget.replace(/\/+$/, '');

    return [
      {
        source: '/api/v1/:path*',
        destination: `${cleanBackend}/api/v1/:path*/`,
      },
      {
        source: '/media/:path*',
        destination: `${cleanBackend}/media/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
