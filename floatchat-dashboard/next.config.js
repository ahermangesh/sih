/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['localhost', '127.0.0.1'],
  },
  env: {
    CUSTOM_KEY: 'my-value',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
  webpack: (config, { isServer }) => {
    // Handle Cesium
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
      }
    }
    
    // Copy Cesium Assets
    const CopyWebpackPlugin = require('copy-webpack-plugin')
    config.plugins.push(
      new CopyWebpackPlugin({
        patterns: [
          {
            from: 'node_modules/cesium/Build/Cesium/Workers',
            to: '../public/cesium/Workers',
          },
          {
            from: 'node_modules/cesium/Build/Cesium/ThirdParty',
            to: '../public/cesium/ThirdParty',
          },
          {
            from: 'node_modules/cesium/Build/Cesium/Assets',
            to: '../public/cesium/Assets',
          },
          {
            from: 'node_modules/cesium/Build/Cesium/Widgets',
            to: '../public/cesium/Widgets',
          },
        ],
      })
    )
    
    return config
  },
}

module.exports = nextConfig