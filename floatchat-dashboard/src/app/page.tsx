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

const Dashboard = dynamic(
  () => import('@/components/Dashboard'),
  { 
    ssr: false,
    loading: () => (
      <div className="h-full bg-gradient-to-br from-blue-50 to-blue-100 dark:from-deep-900 dark:to-deep-800 flex items-center justify-center">
        <div className="text-center">
          <div className="loading-spinner mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading analytics dashboard...</p>
        </div>
      </div>
    )
  }
)



export default function HomePage() {
  const [mounted, setMounted] = useState(false)
  const [show2024Map, setShow2024Map] = useState(true) // Default to showing 2024 data
  const [chatWidth, setChatWidth] = useState(480) // Default chat width for 2-panel layout
  const [dashboardWidth, setDashboardWidth] = useState(420) // Dashboard width when open
  const [isDashboardOpen, setIsDashboardOpen] = useState(false) // Dashboard hidden by default
  const [isResizingChat, setIsResizingChat] = useState(false)
  const [isResizingDashboard, setIsResizingDashboard] = useState(false)
  const chatResizeRef = useRef<HTMLDivElement>(null)
  const dashboardResizeRef = useRef<HTMLDivElement>(null)

  // Handle mouse events for resizing chat panel
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizingChat) return
      
      const newWidth = Math.max(280, Math.min(600, e.clientX)) // Min 280px, Max 600px for chat
      setChatWidth(newWidth)
    }

    const handleMouseUp = () => {
      setIsResizingChat(false)
    }

    if (isResizingChat) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.userSelect = 'none' // Prevent text selection while resizing
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.userSelect = ''
    }
  }, [isResizingChat])

  // Handle mouse events for resizing dashboard panel
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizingDashboard) return
      
      const newWidth = Math.max(320, Math.min(800, window.innerWidth - e.clientX)) // Min 320px, Max 800px for dashboard
      setDashboardWidth(newWidth)
    }

    const handleMouseUp = () => {
      setIsResizingDashboard(false)
    }

    if (isResizingDashboard) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.userSelect = 'none' // Prevent text selection while resizing
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.userSelect = ''
    }
  }, [isResizingDashboard])

  const handleChatMouseDown = () => {
    setIsResizingChat(true)
  }

  const handleDashboardMouseDown = () => {
    setIsResizingDashboard(true)
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
            Dolphin
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
      <div className="h-screen bg-gradient-to-br from-ocean-50 via-white to-deep-50 dark:from-deep-950 dark:via-deep-900 dark:to-deep-800 flex">
        {/* Left Panel - Resizable Chat Interface */}
        <motion.div
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          style={{ width: chatWidth }}
          className="bg-white/50 dark:bg-deep-900/50 backdrop-blur-sm border-r border-white/20 dark:border-gray-700/30 flex-shrink-0 relative"
        >
          <ChatPanel />
          
          {/* Chat Resize Handle */}
          <div
            ref={chatResizeRef}
            onMouseDown={handleChatMouseDown}
            className={`absolute top-0 right-0 w-1 h-full bg-gray-300/50 hover:bg-blue-400 transition-colors cursor-col-resize group ${
              isResizingChat ? 'bg-blue-500' : ''
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

        {/* Middle Panel - Interactive Map (Hidden when dashboard is open) */}
        {!isDashboardOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
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
                
                {/* Panel width indicators */}
                <span className="text-xs text-gray-500 dark:text-gray-400 border-l border-gray-300 dark:border-gray-600 pl-2">
                  Chat: {Math.round(chatWidth)}px
                </span>
              </div>
            </div>

            {/* Dashboard Toggle Button */}
            <div className="absolute top-4 right-4 z-[1002]">
              <button
                onClick={() => setIsDashboardOpen(!isDashboardOpen)}
                className="px-4 py-2 rounded-lg font-medium transition-all duration-300 shadow-lg border bg-white/90 text-gray-700 border-gray-200 hover:bg-white hover:shadow-xl backdrop-blur-sm"
              >
                <div className="flex items-center gap-2">
                  <svg 
                    className="w-4 h-4" 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  Show Dashboard
                </div>
              </button>
            </div>
            
            {show2024Map ? <InteractiveMap2024 /> : <InteractiveMapHardcoded />}
          </motion.div>
        )}

        {/* Dashboard Toggle Button (when dashboard is open) */}
        {isDashboardOpen && (
          <div className="absolute top-4 right-4 z-[1002]">
            <button
              onClick={() => setIsDashboardOpen(!isDashboardOpen)}
              className="px-4 py-2 rounded-lg font-medium transition-all duration-300 shadow-lg border bg-blue-600 text-white border-blue-600 hover:bg-blue-700 backdrop-blur-sm"
            >
              <div className="flex items-center gap-2">
                <svg 
                  className="w-4 h-4 rotate-180" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Hide Dashboard
              </div>
            </button>
          </div>
        )}

        {/* Right Panel - Analytics Dashboard (Conditional) */}
        {isDashboardOpen && (
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 50 }}
            transition={{ 
              duration: 0.4, 
              ease: "easeInOut"
            }}
            className="flex-1 bg-white/50 dark:bg-deep-900/50 backdrop-blur-sm border-l border-white/20 dark:border-gray-700/30 relative overflow-hidden"
          >
            <Dashboard />
          </motion.div>
        )}
      </div>
    </DashboardProvider>
  )
}