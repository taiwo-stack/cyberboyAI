/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracing: false,
  // IMPORTANT: Amplify hosts this as a static Next.js site.
  // Next.js rewrites() are server-only and do NOT run on Amplify static hosting.
  // The API URL is set directly via NEXT_PUBLIC_API_URL in Amplify's environment
  // variables (pointing to the EC2 backend at http://98.94.189.162).
  // See: frontend/lib/api.ts → const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api'
};

export default nextConfig;
