/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  reactStrictMode: true,
  logging: {
    incomingRequests: {
      ignore: [/^\/api\/projects\/[^/?]+\/pages\/[^/?]+\/storyboard\/confirm\/?(?:\?|$)/]
    }
  }
};

export default nextConfig;
