/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  images: {
    domains: [
      'avatars.githubusercontent.com',
      'lh3.googleusercontent.com',
      // Add your Supabase storage domain here
      // 'xxxxx.supabase.co'
    ],
  },
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
  // Enable React Server Components
  // This is the default in Next.js 14+ App Router
}

module.exports = nextConfig
