import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'FloatChat - Ocean Data Explorer',
  description: 'AI-Powered Conversational Interface for ARGO Ocean Data Discovery and Visualization',
  keywords: ['ocean data', 'ARGO floats', 'AI', 'chat interface', 'oceanography', 'marine science'],
  authors: [{ name: 'FloatChat Team' }],
  creator: 'FloatChat Team',
  publisher: 'FloatChat Team',
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'http://localhost:3000',
    title: 'FloatChat - Ocean Data Explorer',
    description: 'AI-Powered Conversational Interface for ARGO Ocean Data Discovery and Visualization',
    siteName: 'FloatChat',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FloatChat - Ocean Data Explorer',
    description: 'AI-Powered Conversational Interface for ARGO Ocean Data Discovery and Visualization',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossOrigin=""
        />
        <script
          src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
          integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
          crossOrigin=""
          async
        />
        <link
          href="https://api.tiles.mapbox.com/mapbox-gl-js/v3.0.1/mapbox-gl.css"
          rel="stylesheet"
        />
      </head>
      <body className={inter.className} suppressHydrationWarning>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}