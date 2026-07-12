/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Produces a minimal, self-contained .next/standalone output (its own
  // node_modules subset + server.js) for the Docker image — without this,
  // the production image would need to copy the entire node_modules tree.
  output: "standalone",

  /**
   * Enable experimental server actions and partial pre-rendering
   * features available in Next.js 14.
   */
  experimental: {
    serverActions: {
      allowedOrigins: ["localhost:3000"],
    },
  },

  /**
   * Public environment variables exposed to the browser bundle.
   * Sensitive values should remain server-only (no NEXT_PUBLIC_ prefix).
   */
  env: {
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
    NEXT_PUBLIC_APP_VERSION: process.env.NEXT_PUBLIC_APP_VERSION,
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  },

  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.supabase.co",
      },
    ],
  },

  // Removed redirects to allow / to render as landing page
};

module.exports = nextConfig;
