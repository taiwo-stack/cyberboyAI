/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracing: false,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://98.94.189.162/:path*', // Proxy to EC2 backend
      },
    ];
  },
};

export default nextConfig;
