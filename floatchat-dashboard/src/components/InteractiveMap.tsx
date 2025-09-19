'use client'

import React, { useState, useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix for default markers
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
})

// ARGO Float interface
interface ArgoFloat {
  id: string
  platform_id: string
  latitude: number
  longitude: number
  last_position_date: string
  status: string
  country?: string
  ocean?: string
  profiles_count?: number
}

const InteractiveMap: React.FC = () => {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const [floats, setFloats] = useState<ArgoFloat[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [show2024Data, setShow2024Data] = useState(false)
  const [selectedMonth, setSelectedMonth] = useState<number | null>(null)

  // Create custom icon for ARGO floats
  const createFloatIcon = (status: string) => {
    const colors = {
      active: '#22c55e',
      inactive: '#ef4444', 
      delayed: '#f59e0b'
    }
    const color = colors[status as keyof typeof colors] || '#6b7280'
    
    return L.divIcon({
      html: `<div style="
        width: 20px;
        height: 20px;
        background-color: ${color};
        border: 2px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
      "></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10],
      className: 'custom-div-icon'
    })
  }

  // Load floats from API
  const loadFloats = async () => {
    try {
      setLoading(true)
      setError(null)
      
      console.log('Fetching floats...', { show2024Data, selectedMonth })
      
      let endpoint = 'http://localhost:8000/api/v1/dashboard/floats/locations'
      if (show2024Data) {
        endpoint = 'http://localhost:8000/api/v1/dashboard/floats/2024'
        if (selectedMonth) {
          endpoint += `?month=${selectedMonth}`
        }
      }
      
      const response = await fetch(endpoint)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      console.log('Float data received:', data)
      
      if (Array.isArray(data) && data.length > 0) {
        setFloats(data)
        console.log(`Loaded ${data.length} floats`)
      } else {
        setError('No float data available')
      }
    } catch (err) {
      console.error('Error loading floats:', err)
      setError('Failed to load float data')
    } finally {
      setLoading(false)
    }
  }

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return

    console.log('Initializing map...')
    
    // Create map
    const map = L.map(mapRef.current, {
      center: [15, 75], // Indian Ocean
      zoom: 5,
      zoomControl: true
    })

    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map)

    mapInstanceRef.current = map
    console.log('Map initialized')

    // Load float data
    loadFloats()

    // Cleanup
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [])

  // Reload data when 2024 toggle or month selection changes
  useEffect(() => {
    if (mapInstanceRef.current) {
      loadFloats()
    }
  }, [show2024Data, selectedMonth])

  // Add markers when floats data changes
  useEffect(() => {
    if (!mapInstanceRef.current || !floats.length) return

    console.log('Adding markers for floats:', floats.length)

    // Clear existing markers
    mapInstanceRef.current.eachLayer((layer) => {
      if (layer instanceof L.Marker) {
        mapInstanceRef.current?.removeLayer(layer)
      }
    })

    // Add new markers
    floats.forEach((float) => {
      if (float.latitude && float.longitude) {
        const marker = L.marker([float.latitude, float.longitude], {
          icon: createFloatIcon(float.status)
        })

        // Add popup
        marker.bindPopup(`
          <div style="padding: 8px;">
            <h3 style="margin: 0 0 8px 0; font-weight: bold;">Float ${float.platform_id}</h3>
            <p style="margin: 4px 0;"><strong>Status:</strong> ${float.status}</p>
            <p style="margin: 4px 0;"><strong>Position:</strong> ${float.latitude.toFixed(3)}°, ${float.longitude.toFixed(3)}°</p>
            <p style="margin: 4px 0;"><strong>Last Update:</strong> ${float.last_position_date}</p>
            ${float.ocean ? `<p style="margin: 4px 0;"><strong>Ocean:</strong> ${float.ocean}</p>` : ''}
            ${float.profiles_count ? `<p style="margin: 4px 0;"><strong>Profiles:</strong> ${float.profiles_count}</p>` : ''}
          </div>
        `)

        marker.addTo(mapInstanceRef.current!)
      }
    })

    // Fit bounds to show all floats
    if (floats.length > 0) {
      const group = new L.FeatureGroup(
        floats
          .filter(f => f.latitude && f.longitude)
          .map(f => L.marker([f.latitude, f.longitude]))
      )
      mapInstanceRef.current.fitBounds(group.getBounds(), { padding: [20, 20] })
    }
  }, [floats])

  return (
    <div className="h-full relative">
      {/* Loading indicator */}
      {loading && (
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-[1001] bg-white rounded-lg p-4 shadow-lg">
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <span className="text-gray-700">Loading floats...</span>
          </div>
        </div>
      )}

      {/* 2024 Data Controls */}
      <div className="absolute top-4 right-4 z-[1001] bg-white border border-gray-200 rounded-lg p-4 shadow-lg">
        <h3 className="text-sm font-medium text-gray-900 mb-3">Data Controls</h3>
        
        {/* 2024 Data Toggle */}
        <div className="flex items-center gap-2 mb-3">
          <input
            type="checkbox"
            id="show2024"
            checked={show2024Data}
            onChange={(e) => setShow2024Data(e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <label htmlFor="show2024" className="text-sm text-gray-700">
            Show 2024 Vector Database Data
          </label>
        </div>

        {/* Month Filter (only when 2024 data is enabled) */}
        {show2024Data && (
          <div className="mt-3">
            <label className="block text-xs text-gray-600 mb-1">Filter by Month:</label>
            <select
              value={selectedMonth || ''}
              onChange={(e) => setSelectedMonth(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Months</option>
              <option value="1">January</option>
              <option value="2">February</option>
              <option value="4">April</option>
              <option value="5">May</option>
              <option value="6">June</option>
              <option value="7">July</option>
              <option value="8">August</option>
              <option value="9">September</option>
              <option value="10">October</option>
              <option value="11">November</option>
              <option value="12">December</option>
            </select>
          </div>
        )}

        {/* Data Info */}
        <div className="mt-3 pt-3 border-t border-gray-200">
          <p className="text-xs text-gray-600">
            {show2024Data ? '2024 Database Profiles' : 'Live Float Positions'}
          </p>
        </div>
      </div>

      {/* Error indicator */}
      {error && (
        <div className="absolute top-4 left-4 z-[1001] bg-red-100 border border-red-300 text-red-800 px-3 py-2 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Float count */}
      {floats.length > 0 && (
        <div className="absolute bottom-4 left-4 z-[1001] bg-white border border-gray-200 rounded-lg p-3 shadow-lg">
          <p className="text-sm font-medium text-gray-900">
            ARGO Floats: {floats.length}
          </p>
          <div className="flex gap-4 mt-2 text-xs">
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              Active: {floats.filter(f => f.status === 'active').length}
            </span>
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
              Inactive: {floats.filter(f => f.status === 'inactive').length}
            </span>
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
              Delayed: {floats.filter(f => f.status === 'delayed').length}
            </span>
          </div>
        </div>
      )}

      {/* Map container */}
      <div
        ref={mapRef}
        className="w-full h-full"
        style={{ minHeight: '400px' }}
      />
    </div>
  )
}

export default InteractiveMap
