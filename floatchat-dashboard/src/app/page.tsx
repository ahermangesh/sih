'use client'

import { useState, useEffect, useRef } from 'react'
import dynamic from 'next/dynamic'
import { motion } from 'framer-motion'
import { DashboardProvider } from '@/context/DashboardContext'

// Dynamic imports to prevent SSR issues
const InteractiveMapHardcoded = dynamic(
  () => import('@/components/InteractiveMapHardcoded'),
  { 
    ssr: false,
    loading: () => (
      <div className="h-full bg-gradient-to-br from-green-100 to-green-200 dark:from-deep-800 dark:to-deep-900 flex items-center justify-center">
        <div className="text-center">
          <div className="loading-spinner mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading live float map...</p>
        </div>
      </div>
    )
  }
)

const InteractiveMap2024 = dynamic(
  () => import('@/components/InteractiveMap2024'),
  { 
    ssr: false,
    loading: () => (
      <div className="h-full bg-gradient-to-br from-blue-100 to-blue-200 dark:from-deep-800 dark:to-deep-900 flex items-center justify-center">
        <div className="text-center">
          <div className="loading-spinner mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading 2024 vector data map...</p>
        </div>
      </div>
    )
  }
)

const ChatPanel = dynamic(
  () => import('@/components/ChatPanel'),
  { 
    ssr: false,
    loading: () => (
      <div className="h-full bg-gradient-to-br from-gray-50 to-gray-100 dark:from-deep-900 dark:to-deep-800 flex items-center justify-center">
        <div className="text-center">
          <div className="loading-spinner mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading chat interface...</p>
        </div>
      </div>
    )
  }
)



export default function HomePage() {
  const [mounted, setMounted] = useState(false)
  const [show2024Map, setShow2024Map] = useState(true) // Default to showing 2024 data
  const [chatWidth, setChatWidth] = useState(480) // Default wider width (30rem = 480px)
  const [isResizing, setIsResizing] = useState(false)
  const resizeRef = useRef<HTMLDivElement>(null)

  // Handle mouse events for resizing
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return
      
      const newWidth = Math.max(320, Math.min(800, e.clientX)) // Min 320px, Max 800px
      setChatWidth(newWidth)
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.userSelect = 'none' // Prevent text selection while resizing
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.userSelect = ''
    }
  }, [isResizing])

  const handleMouseDown = () => {
    setIsResizing(true)
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      setMounted(true)
    }, 100) // Small delay to ensure proper hydration
    
    return () => clearTimeout(timer)
  }, [])

  if (!mounted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-ocean-50 via-white to-deep-50 dark:from-deep-950 dark:via-deep-900 dark:to-deep-800 flex items-center justify-center">
        <div className="text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            className="w-16 h-16 border-4 border-ocean-200 border-t-ocean-500 rounded-full mx-auto mb-4"
          />
          <h1 className="text-2xl font-bold text-gray-800 dark:text-white mb-2">
            FloatChat
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Loading Ocean Data Explorer...
          </p>
        </div>
      </div>
    )
  }

  return (
    <DashboardProvider>
      <div className="min-h-screen bg-gradient-to-br from-ocean-50 via-white to-deep-50 dark:from-deep-950 dark:via-deep-900 dark:to-deep-800">
      {/* Header */}
      <header className="glass-effect border-b border-white/20 dark:border-gray-700/30 p-4 sticky top-0 z-50">
        <div className="flex items-center justify-between">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center space-x-3"
          >
            <div className="w-10 h-10 bg-gradient-to-br from-ocean-400 to-ocean-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">🌊</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-800 dark:text-white">
                FloatChat
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Ocean Data Explorer
              </p>
            </div>
          </motion.div>
          
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center space-x-4"
          >
            <div className="hidden md:flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span>Connected to API</span>
            </div>
            <button
              className="p-2 hover:bg-white/10 dark:hover:bg-gray-800/50 rounded-lg transition-colors"
              title="Settings"
            >
              ⚙️
            </button>
          </motion.div>
        </div>
      </header>

      {/* Main Layout */}
      <div className="h-[calc(100vh-80px)] flex">
        {/* Left Panel - Resizable Chat Interface */}
        <motion.div
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          style={{ width: chatWidth }}
          className="bg-white/50 dark:bg-deep-900/50 backdrop-blur-sm border-r border-white/20 dark:border-gray-700/30 flex-shrink-0 relative"
        >
          <ChatPanel />
          
          {/* Resize Handle */}
          <div
            ref={resizeRef}
            onMouseDown={handleMouseDown}
            className={`absolute top-0 right-0 w-1 h-full bg-gray-300/50 hover:bg-blue-400 transition-colors cursor-col-resize group ${
              isResizing ? 'bg-blue-500' : ''
            }`}
            title="Drag to resize chat panel"
          >
            {/* Visual resize indicator */}
            <div className="absolute right-0 top-1/2 transform translate-x-1/2 -translate-y-1/2 w-4 h-8 bg-gray-400/20 rounded-full group-hover:bg-blue-400/30 transition-colors flex items-center justify-center">
              <svg className="w-2 h-4 text-gray-500 group-hover:text-blue-600" fill="currentColor" viewBox="0 0 6 16">
                <circle cx="1" cy="4" r="1"/>
                <circle cx="1" cy="8" r="1"/>
                <circle cx="1" cy="12" r="1"/>
                <circle cx="5" cy="4" r="1"/>
                <circle cx="5" cy="8" r="1"/>
                <circle cx="5" cy="12" r="1"/>
              </svg>
            </div>
          </div>
        </motion.div>

        {/* Middle Panel - Interactive Map */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex-1 min-w-0 relative"
        >
          {/* Map Toggle Button */}
          <div className="absolute top-4 left-4 z-[1002] bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
            <div className="flex items-center space-x-2 p-2">
              <button
                onClick={() => setShow2024Map(!show2024Map)}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                  show2024Map 
                    ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' 
                    : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                }`}
              >
                {show2024Map ? '2024 Vector Data' : 'Live Float Data'}
              </button>
              
              {/* Chat width indicator */}
              <span className="text-xs text-gray-500 dark:text-gray-400 border-l border-gray-300 dark:border-gray-600 pl-2">
                Chat: {Math.round(chatWidth)}px
              </span>
            </div>
          </div>
          
          {show2024Map ? <InteractiveMap2024 /> : <InteractiveMapHardcoded />}
        </motion.div>
      </div>
    </div>
    </DashboardProvider>
  )
}