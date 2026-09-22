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
    // BACKEND_INTERNAL_URL must be set in Vercel dashboard for production.
    // It should be the bare Render URL, e.g. https://bharath-masala-api.onrender.com
    const backendTarget =
      process.env.BACKEND_INTERNAL_URL ||
      (process.env.NODE_ENV !== 'production'
        ? 'http://127.0.0.1:8000'
        : null);

    if (!backendTarget) {
      console.error(
        '[next.config.js] BACKEND_INTERNAL_URL is not set! ' +
          'API proxying is DISABLED. Set this env var in the Vercel dashboard.'
      );
      return [];
    }

    let cleanBackend = backendTarget.replace(/\/+$/, '');
    if (!/^https?:\/\//i.test(cleanBackend)) {
      cleanBackend = `http://${cleanBackend}`;
    }
    const serverRoot = cleanBackend.replace(/\/api$/, '');

    return {
      beforeFiles: [
        // Django Administration
        {
          source: '/admin',
          destination: `${serverRoot}/admin/`,
        },
        {
          source: '/admin/:path*',
          destination: `${serverRoot}/admin/:path*/`,
        },
        // Django REST API
        {
          source: '/api',
          destination: `${serverRoot}/api/`,
        },
        {
          source: '/api/:path*',
          destination: `${serverRoot}/api/:path*/`,
        },
        // Static assets for Django Admin & DRF
        {
          source: '/static/admin/:path*',
          destination: `${serverRoot}/static/admin/:path*`,
        },
        {
          source: '/static/rest_framework/:path*',
          destination: `${serverRoot}/static/rest_framework/:path*`,
        },
        // Media files (product photos, invoices)
        {
          source: '/media/:path*',
          destination: `${serverRoot}/media/:path*`,
        },
        // Health check probes
        {
          source: '/health',
          destination: `${serverRoot}/health/`,
        },
        {
          source: '/health/:path*',
          destination: `${serverRoot}/health/:path*`,
        },
      ],
    };
  },
};

module.exports = nextConfig;
