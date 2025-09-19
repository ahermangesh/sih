'use client'

import { useState, useEffect, useCallback } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import { Icon, LatLngBounds } from 'leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import { motion } from 'framer-motion'
import type { FloatData } from '@/types'

// Mock data for development
const mockFloats: FloatData[] = []

export default function InteractiveMap() {
  const [floats, setFloats] = useState<FloatData[]>(mockFloats)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedFloat, setSelectedFloat] = useState<FloatData | null>(null)
  const [show3D, setShow3D] = useState(false)
  const [clustering, setClustering] = useState(true)
  const [connectionStatus, setConnectionStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking')

  useEffect(() => {
    loadFloats()
    checkConnection()
  }, [])

  const checkConnection = async () => {
    try {
      const apiService = (await import('@/lib/api')).default
      const isConnected = await apiService.checkConnection()
      setConnectionStatus(isConnected ? 'connected' : 'disconnected')
    } catch {
      setConnectionStatus('disconnected')
    }
  }

  const loadFloats = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const apiService = (await import('@/lib/api')).default
      const floatData = await apiService.getFloats({
        status: ['active', 'inactive', 'delayed'],
        boundingBox: {
          north: 80,
          south: -80,
          east: 180,
          west: -180
        }
      })
      
      // Filter out floats without valid coordinates
      const validFloats = floatData.filter(float => 
        float.latitude && float.longitude && 
        Math.abs(float.latitude) <= 90 && 
        Math.abs(float.longitude) <= 180
      )
      
      setFloats(validFloats)
      
      if (validFloats.length === 0) {
        setError('No float data available. Please check backend connection.')
      }
    } catch (err) {
      console.error('Failed to load floats:', err)
      setError('Failed to load float data. Backend server may be offline.')
      setConnectionStatus('disconnected')
      // Use mock data as fallback
      setFloats([
        {
          id: 'demo_001',
          platform_id: '2903378',
          latitude: 20.5,
          longitude: -30.2,
          last_position_date: '2025-09-19',
          status: 'active',
          country: 'Demo',
          ocean: 'Atlantic',
          profiles_count: 150,
        },
        {
          id: 'demo_002',
          platform_id: '6903240',
          latitude: 35.7,
          longitude: -25.1,
          last_position_date: '2025-09-18',
          status: 'active',
          country: 'Demo',
          ocean: 'Atlantic',
          profiles_count: 200,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

// Custom icons for different float statuses
const createFloatIcon = (status: string, size: number = 25) => {
  const colors = {
    active: '#22c55e',
    inactive: '#ef4444',
    delayed: '#f59e0b',
    stopped: '#6b7280',
  }
  
  const color = colors[status as keyof typeof colors] || colors.stopped
  
  return new Icon({
    iconUrl: `data:image/svg+xml;base64,${btoa(`
      <svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" fill="${color}" stroke="white" stroke-width="2"/>
        <circle cx="12" cy="12" r="6" fill="white" opacity="0.8"/>
        <circle cx="12" cy="12" r="3" fill="${color}"/>
      </svg>
    `)}`,
    iconSize: [size, size],
    iconAnchor: [size/2, size/2],
    popupAnchor: [0, -size/2],
  })
}

interface MapControlsProps {
  onToggle3D: () => void
  onToggleClustering: () => void
  onFitBounds: () => void
  show3D: boolean
  clustering: boolean
}

function MapControls({ onToggle3D, onToggleClustering, onFitBounds, show3D, clustering }: MapControlsProps) {
  return (
    <div className="map-controls">
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={onToggle3D}
        className={`control-button ${show3D ? 'bg-ocean-500 text-white' : ''}`}
        title="Toggle 3D View"
      >
        🌐
      </motion.button>
      
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={onToggleClustering}
        className={`control-button ${clustering ? 'bg-ocean-500 text-white' : ''}`}
        title="Toggle Clustering"
      >
        📍
      </motion.button>
      
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={onFitBounds}
        className="control-button"
        title="Fit All Floats"
      >
        🎯
      </motion.button>
    </div>
  )
}

function FitBoundsComponent({ floats }: { floats: FloatData[] }) {
  const map = useMap()
  
  const fitToFloats = useCallback(() => {
    if (floats.length === 0) return
    
    const bounds = new LatLngBounds(
      floats.map(float => [float.latitude, float.longitude])
    )
    map.fitBounds(bounds, { padding: [50, 50] })
  }, [map, floats])
  
  useEffect(() => {
    fitToFloats()
  }, [fitToFloats])
  
  return null
}

export default function InteractiveMap() {
  const [floats, setFloats] = useState<FloatData[]>(mockFloats)
  const [selectedFloat, setSelectedFloat] = useState<FloatData | null>(null)
  const [show3D, setShow3D] = useState(false)
  const [clustering, setClustering] = useState(true)
  const [mapInstance, setMapInstance] = useState<any>(null)

  const handleFloatClick = (float: FloatData) => {
    setSelectedFloat(float)
  }

  const handleFitBounds = () => {
    if (mapInstance && floats.length > 0) {
      const bounds = new LatLngBounds(
        floats.map(float => [float.latitude, float.longitude])
      )
      mapInstance.fitBounds(bounds, { padding: [50, 50] })
    }
  }

  const FloatMarkers = () => {
    const markers = floats.map((float) => (
      <Marker
        key={float.id}
        position={[float.latitude, float.longitude]}
        icon={createFloatIcon(float.status)}
        eventHandlers={{
          click: () => handleFloatClick(float),
        }}
      >
        <Popup>
          <div className="p-3 min-w-[220px]">
            <h3 className="font-bold text-lg mb-2 text-ocean-700">
              Float {float.platform_id}
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Status:</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  float.status === 'active' ? 'bg-green-100 text-green-800' :
                  float.status === 'delayed' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {float.status}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Ocean:</span>
                <span className="font-medium">{float.ocean}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Country:</span>
                <span className="font-medium">{float.country}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Profiles:</span>
                <span className="font-medium">{float.profiles_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Position:</span>
                <span className="font-medium text-xs">
                  {float.latitude.toFixed(2)}°, {float.longitude.toFixed(2)}°
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Last Update:</span>
                <span className="font-medium">{float.last_position_date}</span>
              </div>
            </div>
            <div className="flex space-x-2 mt-3">
              <button
                onClick={() => setSelectedFloat(float)}
                className="flex-1 bg-ocean-500 hover:bg-ocean-600 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                View Details
              </button>
              <button
                className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm transition-colors"
                title="Center on map"
              >
                🎯
              </button>
            </div>
          </div>
        </Popup>
      </Marker>
    ))

    return clustering ? (
      <MarkerClusterGroup chunkedLoading>
        {markers}
      </MarkerClusterGroup>
    ) : (
      <>{markers}</>
    )
  }

  return (
    <div className="h-full relative bg-gradient-to-br from-ocean-50 to-ocean-100 dark:from-deep-800 dark:to-deep-900">
      <MapContainer
        center={[20, -30]}
        zoom={3}
        className="h-full w-full rounded-none"
        ref={setMapInstance}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        <FloatMarkers />
        <FitBoundsComponent floats={floats} />
      </MapContainer>

      <MapControls
        onToggle3D={() => setShow3D(!show3D)}
        onToggleClustering={() => setClustering(!clustering)}
        onFitBounds={handleFitBounds}
        show3D={show3D}
        clustering={clustering}
      />

      {/* Enhanced Legend */}
      <div className="absolute bottom-4 left-4 z-[1000]">
        <div className="bg-white/90 dark:bg-deep-900/90 backdrop-blur-md rounded-lg p-4 max-w-xs shadow-lg border border-white/20 dark:border-gray-700/30">
          <h4 className="font-semibold text-gray-800 dark:text-white mb-3 text-sm">
            ARGO Float Status
          </h4>
          <div className="space-y-2 text-sm">
            {[
              { status: 'active', label: 'Active', color: '#22c55e', count: mockFloats.filter(f => f.status === 'active').length },
              { status: 'delayed', label: 'Delayed', color: '#f59e0b', count: mockFloats.filter(f => f.status === 'delayed').length },
              { status: 'inactive', label: 'Inactive', color: '#ef4444', count: mockFloats.filter(f => f.status === 'inactive').length },
              { status: 'stopped', label: 'Stopped', color: '#6b7280', count: mockFloats.filter(f => f.status === 'stopped').length },
            ].map(({ status, label, color, count }) => (
              <div key={status} className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div
                    className="w-3 h-3 rounded-full border border-white shadow-sm"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-gray-700 dark:text-gray-300">{label}</span>
                </div>
                <span className="text-xs font-medium bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded-full">
                  {count}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            <div className="text-xs text-gray-600 dark:text-gray-400">
              Total: {mockFloats.length} floats
            </div>
          </div>
        </div>
      </div>

      {/* Map Info Panel */}
      <div className="absolute top-4 left-4 z-[1000]">
        <div className="bg-white/90 dark:bg-deep-900/90 backdrop-blur-md rounded-lg p-3 shadow-lg border border-white/20 dark:border-gray-700/30">
          <h4 className="font-semibold text-gray-800 dark:text-white text-sm mb-1">
            Ocean Data Explorer
          </h4>
          <div className="text-xs text-gray-600 dark:text-gray-400">
            Interactive ARGO Float Map
          </div>
          <div className="flex items-center space-x-4 mt-2 text-xs">
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span>Live Data</span>
            </div>
            <div className="flex items-center space-x-1">
              <span>Zoom: {mapInstance?.getZoom?.() || 3}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}