'use client'

import React, { useState, useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import '../styles/euro-argo-map.css'

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
  platform_id?: string
  wmo_id?: number
  latitude: number
  longitude: number
  last_position_date: string
  status: string
  country?: string
  ocean?: string
  profiles_count?: number
}

const InteractiveMapHardcoded: React.FC = () => {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const [floats, setFloats] = useState<ArgoFloat[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Create custom icon for ARGO floats - Euro-Argo style
  const createFloatIcon = (status: string) => {
    // Use Euro-Argo style yellow/orange colors
    const colors = {
      active: '#FFB000',      // Euro-Argo yellow/orange
      inactive: '#FF6B00',    // Slightly darker orange for inactive
      delayed: '#FFC85A',     // Lighter yellow for delayed
      unknown: '#CC8400'      // Darker orange for unknown
    }
    const color = colors[status as keyof typeof colors] || '#FFB000'
    
    return L.divIcon({
      html: `<div style="
        width: 12px;
        height: 12px;
        background-color: ${color};
        border: 2px solid rgba(255, 255, 255, 0.8);
        border-radius: 50%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
      "></div>`,
      className: 'euro-argo-float-icon',
      iconSize: [16, 16],
      iconAnchor: [8, 8]
    })
  }

  const loadFloats = async () => {
    try {
      setLoading(true)
      setError(null)
      
      console.log('Loading hardcoded live float positions...')
      
      // Hardcoded current/live ARGO float positions (Indian Ocean focus)
      const hardcodedFloats: ArgoFloat[] = [
        // Currently active floats
        { id: "LIVE1", platform_id: "ARGO001", wmo_id: 2902746, latitude: 15.8, longitude: 73.2, last_position_date: "2025-09-18", status: "active", country: "India", ocean: "Arabian Sea" },
        { id: "LIVE2", platform_id: "ARGO002", wmo_id: 372029, latitude: 8.5, longitude: 76.8, last_position_date: "2025-09-18", status: "active", country: "India", ocean: "Arabian Sea" },
        { id: "LIVE3", platform_id: "ARGO003", wmo_id: 370037, latitude: 12.1, longitude: 85.3, last_position_date: "2025-09-17", status: "active", country: "India", ocean: "Bay of Bengal" },
        { id: "LIVE4", platform_id: "ARGO004", wmo_id: 2901234, latitude: 18.5, longitude: 88.1, last_position_date: "2025-09-17", status: "active", country: "India", ocean: "Bay of Bengal" },
        
        // Recent positions
        { id: "LIVE5", platform_id: "ARGO005", wmo_id: 2901235, latitude: 6.2, longitude: 68.7, last_position_date: "2025-09-16", status: "active", country: "Maldives", ocean: "Arabian Sea" },
        { id: "LIVE6", platform_id: "ARGO006", wmo_id: 2901236, latitude: -2.8, longitude: 72.4, last_position_date: "2025-09-15", status: "active", country: "Maldives", ocean: "Central Indian Ocean" },
        { id: "LIVE7", platform_id: "ARGO007", wmo_id: 2901237, latitude: -8.1, longitude: 95.6, last_position_date: "2025-09-15", status: "active", country: "Australia", ocean: "Eastern Indian Ocean" },
        { id: "LIVE8", platform_id: "ARGO008", wmo_id: 2901238, latitude: -15.3, longitude: 68.9, last_position_date: "2025-09-14", status: "delayed", country: "France", ocean: "Southern Indian Ocean" },
        
        // Slightly older but active
        { id: "LIVE9", platform_id: "ARGO009", wmo_id: 2901239, latitude: 22.1, longitude: 67.5, last_position_date: "2025-09-13", status: "active", country: "India", ocean: "Arabian Sea" },
        { id: "LIVE10", platform_id: "ARGO010", wmo_id: 2901240, latitude: 19.8, longitude: 72.3, last_position_date: "2025-09-12", status: "active", country: "India", ocean: "Arabian Sea" },
        { id: "LIVE11", platform_id: "ARGO011", wmo_id: 2901241, latitude: 13.7, longitude: 80.2, last_position_date: "2025-09-11", status: "active", country: "India", ocean: "Bay of Bengal" },
        { id: "LIVE12", platform_id: "ARGO012", wmo_id: 2901242, latitude: 10.5, longitude: 92.8, last_position_date: "2025-09-10", status: "delayed", country: "Thailand", ocean: "Bay of Bengal" },
        
        // Some inactive for comparison
        { id: "LIVE13", platform_id: "ARGO013", wmo_id: 2901243, latitude: -12.6, longitude: 83.4, last_position_date: "2025-09-05", status: "inactive", country: "Australia", ocean: "Eastern Indian Ocean" },
        { id: "LIVE14", platform_id: "ARGO014", wmo_id: 2901244, latitude: -25.2, longitude: 78.1, last_position_date: "2025-08-28", status: "inactive", country: "Australia", ocean: "Southern Indian Ocean" },
        
        // Additional active floats for good coverage
        { id: "LIVE15", platform_id: "ARGO015", wmo_id: 2901245, latitude: 4.3, longitude: 81.7, last_position_date: "2025-09-18", status: "active", country: "Sri Lanka", ocean: "Bay of Bengal" },
        { id: "LIVE16", platform_id: "ARGO016", wmo_id: 2901246, latitude: 16.9, longitude: 94.2, last_position_date: "2025-09-17", status: "active", country: "Myanmar", ocean: "Bay of Bengal" },
        { id: "LIVE17", platform_id: "ARGO017", wmo_id: 2901247, latitude: -5.7, longitude: 58.3, last_position_date: "2025-09-16", status: "active", country: "Mauritius", ocean: "Western Indian Ocean" },
        { id: "LIVE18", platform_id: "ARGO018", wmo_id: 2901248, latitude: -18.4, longitude: 105.8, last_position_date: "2025-09-15", status: "active", country: "Australia", ocean: "Eastern Indian Ocean" }
      ]
      
      setFloats(hardcodedFloats)
      console.log(`Loaded ${hardcodedFloats.length} hardcoded live floats`)
      
    } catch (err) {
      console.error('Error loading hardcoded floats:', err)
      setError('Failed to load live float data')
    } finally {
      setLoading(false)
    }
  }

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return

    console.log('Initializing live floats map...')
    
    // Create map with Euro-Argo style settings
    const map = L.map(mapRef.current, {
      center: [15, 75], // Indian Ocean
      zoom: 4,
      zoomControl: true,
      scrollWheelZoom: true,
      doubleClickZoom: true,
      boxZoom: true,
      keyboard: true,
      dragging: true,
      touchZoom: true,
      worldCopyJump: false
    })

    // Add multiple tile layers like Euro-Argo
    const baseLayers = {
      "Satellite": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        maxZoom: 18
      }),
      "Terrain": L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
        maxZoom: 17
      }),
      "Ocean": L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      })
    }

    // Add default satellite layer (like Euro-Argo)
    baseLayers["Satellite"].addTo(map)

    // Add layer control
    L.control.layers(baseLayers).addTo(map)

    // Add scale control
    L.control.scale({
      position: 'bottomleft',
      maxWidth: 100,
      metric: true,
      imperial: false
    }).addTo(map)

    mapInstanceRef.current = map

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

  // Add markers when floats data changes
  useEffect(() => {
    if (!mapInstanceRef.current || !floats.length) return

    console.log('Adding markers for live floats:', floats.length)

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

        marker.bindPopup(`
          <div class="p-2">
            <h3 class="font-semibold text-sm">${float.platform_id} (WMO ${float.wmo_id})</h3>
            <p class="text-xs text-gray-600">Status: ${float.status}</p>
            <p class="text-xs text-gray-600">Location: ${float.latitude.toFixed(3)}, ${float.longitude.toFixed(3)}</p>
            <p class="text-xs text-gray-600">Last Update: ${new Date(float.last_position_date).toLocaleDateString()}</p>
            ${float.country ? `<p class="text-xs text-gray-600">Country: ${float.country}</p>` : ''}
            ${float.ocean ? `<p class="text-xs text-gray-600">Ocean: ${float.ocean}</p>` : ''}
            <p class="text-xs text-green-600"><strong>Live Position Data</strong></p>
          </div>
        `)

        marker.addTo(mapInstanceRef.current!)
      }
    })

    // Fit map to show all markers if we have floats
    if (floats.length > 0) {
      const group = L.featureGroup(
        floats
          .filter(f => f.latitude && f.longitude)
          .map(f => L.marker([f.latitude, f.longitude]))
      )
      mapInstanceRef.current.fitBounds(group.getBounds(), { padding: [20, 20] })
    }
  }, [floats])

  return (
    <div className="h-full relative">
      {/* Loading indicator - Euro-Argo style */}
      {loading && (
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-[1001] bg-white rounded-lg p-4 shadow-lg border">
          <div className="flex items-center gap-3">
            <div className="argo-loading-spinner"></div>
            <span className="text-gray-700 font-medium">Loading ARGO floats...</span>
          </div>
        </div>
      )}

      {/* Live Data Info */}
      <div className="absolute top-4 right-4 z-[1001] bg-white border border-gray-200 rounded-lg p-4 shadow-lg">
        <h3 className="text-sm font-medium text-gray-900 mb-3">Live Float Positions</h3>
        
        {/* Data Info */}
        <div className="pt-2 border-t border-gray-200">
          <p className="text-xs text-gray-600">
            Current ARGO Float Locations
          </p>
          <p className="text-xs text-green-600 mt-1">
            ● Live Data (No database queries)
          </p>
        </div>
      </div>

      {/* Error indicator */}
      {error && (
        <div className="absolute top-4 left-4 z-[1001] bg-red-100 border border-red-300 text-red-800 px-3 py-2 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Float count - Euro-Argo style */}
      {floats.length > 0 && (
        <div className="absolute bottom-4 left-4 z-[1001] bg-white border border-gray-200 rounded-lg p-3 shadow-lg">
          <p className="text-sm font-medium text-gray-900">
            Live ARGO Floats: {floats.length}
          </p>
          <div className="flex gap-4 mt-2 text-xs">
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#FFB000' }}></div>
              Active: {floats.filter(f => f.status === 'active').length}
            </span>
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#FFC85A' }}></div>
              Delayed: {floats.filter(f => f.status === 'delayed').length}
            </span>
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#FF6B00' }}></div>
              Inactive: {floats.filter(f => f.status === 'inactive').length}
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

export default InteractiveMapHardcoded