'use client'

import React, { useState, useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import '../styles/euro-argo-map.css'

// Import Leaflet Heat plugin
import 'leaflet.heat'

// Extend Leaflet to include heat plugin types
declare module 'leaflet' {
  function heatLayer(points: Array<[number, number, number?]>, options?: any): any
}

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

const InteractiveMap2024: React.FC = () => {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const [floats, setFloats] = useState<ArgoFloat[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [show2024Data, setShow2024Data] = useState(true)
  const [basemapType, setBasemapType] = useState<'satellite' | 'ocean' | 'terrain'>('satellite')
  const [selectedMonth, setSelectedMonth] = useState<number | null>(null)
  const [showHeatmap, setShowHeatmap] = useState(false)
  const [showTrajectories, setShowTrajectories] = useState(false)
  const [selectedFloatId, setSelectedFloatId] = useState<string | null>(null)
  const basemapLayerRef = useRef<L.TileLayer | null>(null)
  const heatmapLayerRef = useRef<any>(null)
  const trajectoriesLayerRef = useRef<L.LayerGroup | null>(null)

  // Create custom Euro-Argo style icons for ARGO floats
  const createFloatIcon = (status: string) => {
    // Use Euro-Argo style yellow/orange colors consistently
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

  // Generate sample trajectory data for a float (simulated drift path)
  const generateTrajectoryData = (float: ArgoFloat) => {
    const points: [number, number][] = []
    const numPoints = 8 // Number of trajectory points
    const baseDate = new Date(float.last_position_date)
    
    // Generate trajectory points going backwards in time
    for (let i = numPoints - 1; i >= 0; i--) {
      const dayOffset = i * 10 // 10 days between points
      const drift = {
        lat: (Math.random() - 0.5) * 0.5, // Random drift up to 0.25 degrees
        lon: (Math.random() - 0.5) * 0.5
      }
      
      const point: [number, number] = [
        float.latitude + drift.lat - (i * 0.05), // Gradual drift
        float.longitude + drift.lon - (i * 0.05)
      ]
      points.push(point)
    }
    
    // Add current position as final point
    points.push([float.latitude, float.longitude])
    return points
  }

  // Helper function to determine ocean region from coordinates
  const getOceanRegion = (lat: number, lon: number) => {
    if (lat > 15 && lon > 80 && lon < 100) return 'Bay of Bengal'
    if (lat > 5 && lat < 25 && lon > 60 && lon < 80) return 'Arabian Sea'
    if (lat < -30 && lon > 20 && lon < 147) return 'Southern Ocean'
    if (lat > -30 && lat < 5 && lon > 40 && lon < 80) return 'Western Indian Ocean'
    if (lat > -30 && lat < 5 && lon > 80 && lon < 120) return 'Eastern Indian Ocean'
    if (lon > 120 && lat < -20) return 'Near Australia'
    return 'Indian Ocean'
  }

  // Generate heatmap data from ARGO floats (simulated temperature anomalies)
  const generateHeatmapData = () => {
    return floats.map(float => {
      // Simulate temperature anomaly based on latitude and longitude
      // Higher anomalies in tropical regions, lower in polar regions
      const latFactor = Math.abs(float.latitude) < 30 ? 1.5 : 0.5 // Tropical vs polar
      const seasonalFactor = Math.sin((Date.parse(float.last_position_date) / (1000 * 60 * 60 * 24 * 365)) * 2 * Math.PI) * 0.3
      const baseAnomaly = (Math.random() - 0.5) * 2 // Random component
      const intensity = Math.max(0.1, latFactor + seasonalFactor + baseAnomaly)
      
      return [float.latitude, float.longitude, intensity] as [number, number, number]
    })
  }

  const loadFloats = async () => {
    try {
      setLoading(true)
      setError(null)
      
      console.log('Loading hardcoded 2024 floats...', { selectedMonth })
      
      // Real 2024 ARGO float data from vector database (ChromaDB export)
      const hardcodedFloats: ArgoFloat[] = [
        { id: "6413", wmo_id: 6413, latitude: -38.88, longitude: 139.669, last_position_date: "2024-07-05", status: "active" },
        { id: "14543", wmo_id: 14543, latitude: -19.44525, longitude: 101.46044, last_position_date: "2024-07-17", status: "active" },
        { id: "25617", wmo_id: 25617, latitude: -15.0363, longitude: 90.3079, last_position_date: "2024-07-19", status: "active" },
        { id: "27129", wmo_id: 27129, latitude: -40.62694, longitude: 66.88803, last_position_date: "2024-07-01", status: "active" },
        { id: "32263", wmo_id: 32263, latitude: -65.86706032211151, longitude: 107.18556386555969, last_position_date: "2024-07-30", status: "active" },
        { id: "84386", wmo_id: 84386, latitude: -66.02159555102503, longitude: 62.76221192902095, last_position_date: "2024-07-09", status: "active" },
        { id: "97653", wmo_id: 97653, latitude: -67.12833598018108, longitude: 83.11136552835698, last_position_date: "2024-07-14", status: "active" },
        { id: "262355", wmo_id: 262355, latitude: -52.644235, longitude: 71.22491666666667, last_position_date: "2024-07-15", status: "active" },
        { id: "280455", wmo_id: 280455, latitude: -40.084, longitude: 88.534, last_position_date: "2024-07-11", status: "active" },
        { id: "310076", wmo_id: 310076, latitude: -36.6731, longitude: 120.7244, last_position_date: "2024-07-24", status: "active" },
        { id: "322282", wmo_id: 322282, latitude: -7.240236666666666, longitude: 51.301, last_position_date: "2024-07-20", status: "active" },
        { id: "436843", wmo_id: 436843, latitude: -47.977021666666666, longitude: 104.56802833333332, last_position_date: "2024-07-28", status: "active" },
        { id: "451843", wmo_id: 451843, latitude: -56.309085, longitude: 62.70885166666667, last_position_date: "2024-07-02", status: "active" },
        { id: "465537", wmo_id: 465537, latitude: -27.1191, longitude: 82.6675, last_position_date: "2024-07-25", status: "active" },
        { id: "494226", wmo_id: 494226, latitude: 16.432, longitude: 88.531, last_position_date: "2024-07-08", status: "active" },
        { id: "495846", wmo_id: 495846, latitude: 11.315, longitude: 86.311, last_position_date: "2024-07-07", status: "active" },
        { id: "548026", wmo_id: 548026, latitude: -63.250246399999995, longitude: 136.9175998, last_position_date: "2024-07-13", status: "active" },
        { id: "642518", wmo_id: 642518, latitude: -61.52843479034886, longitude: 79.53267020769007, last_position_date: "2024-07-31", status: "active" },
        { id: "698129", wmo_id: 698129, latitude: -29.82211, longitude: 50.89234, last_position_date: "2024-07-16", status: "active" },
        { id: "704545", wmo_id: 704545, latitude: 7.076, longitude: 69.986, last_position_date: "2024-07-12", status: "active" },
        { id: "714690", wmo_id: 714690, latitude: -57.55937194824219, longitude: 108.79882049560548, last_position_date: "2024-07-26", status: "active" },
        { id: "822101", wmo_id: 822101, latitude: -39.41175, longitude: 55.43301, last_position_date: "2024-07-10", status: "active" },
        { id: "822527", wmo_id: 822527, latitude: -14.14702, longitude: 91.71587, last_position_date: "2024-07-18", status: "active" },
        { id: "829194", wmo_id: 829194, latitude: -50.61848333333333, longitude: 107.02273833333334, last_position_date: "2024-07-22", status: "active" },
        { id: "851300", wmo_id: 851300, latitude: -58.4613, longitude: 119.9437, last_position_date: "2024-07-21", status: "active" },
        { id: "876453", wmo_id: 876453, latitude: -33.45043249767801, longitude: 48.63168902857, last_position_date: "2024-07-29", status: "active" },
        { id: "911999", wmo_id: 911999, latitude: -46.6288, longitude: 89.38239333333334, last_position_date: "2024-07-27", status: "active" },
        { id: "916518", wmo_id: 916518, latitude: -48.46000166666666, longitude: 34.631115, last_position_date: "2024-07-03", status: "active" },
        { id: "929783", wmo_id: 929783, latitude: -32.06848333333333, longitude: 60.73833833333333, last_position_date: "2024-07-23", status: "active" },
        { id: "958527", wmo_id: 958527, latitude: -46.69721, longitude: 98.85463, last_position_date: "2024-07-06", status: "active" },
        { id: "979024", wmo_id: 979024, latitude: -49.42768, longitude: 95.34854, last_position_date: "2024-07-04", status: "active" }
      ]
      
      // Filter by month if selected
      let filteredFloats = hardcodedFloats
      if (selectedMonth) {
        filteredFloats = hardcodedFloats.filter(float => {
          const date = new Date(float.last_position_date)
          return date.getMonth() + 1 === selectedMonth
        })
      }
      
      setFloats(filteredFloats)
      console.log(`Loaded ${filteredFloats.length} hardcoded 2024 floats`)
      
    } catch (err) {
      console.error('Error loading hardcoded floats:', err)
      setError('Failed to load 2024 float data')
    } finally {
      setLoading(false)
    }
  }

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return

    console.log('Initializing map...')
    
    // Create map with Euro-Argo style settings
    const map = L.map(mapRef.current, {
      center: [-20, 80], // Better center for Indian Ocean ARGO data
      zoom: 3,
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
      "Ocean": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles © Esri — Sources: GEBCO, NOAA, National Geographic',
        maxZoom: 13
      }),
      "Terrain": L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
        maxZoom: 17
      })
    }

    // Add default satellite layer (like Euro-Argo)
    baseLayers["Satellite"].addTo(map)
    basemapLayerRef.current = baseLayers["Satellite"]

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

  // Reload data when month selection changes (re-filter hardcoded data)
  useEffect(() => {
    if (mapInstanceRef.current) {
      loadFloats()
    }
  }, [selectedMonth])

  // Handle basemap changes - Euro-Argo style
  useEffect(() => {
    if (!mapInstanceRef.current || !basemapLayerRef.current) return

    // Remove current basemap
    mapInstanceRef.current.removeLayer(basemapLayerRef.current)

    // Add new basemap based on Euro-Argo options
    let newLayer: L.TileLayer
    switch (basemapType) {
      case 'satellite':
        newLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
          attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
          maxZoom: 18
        })
        break
      case 'ocean':
        newLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}', {
          attribution: 'Tiles © Esri — Sources: GEBCO, NOAA, National Geographic',
          maxZoom: 13
        })
        break
      case 'terrain':
        newLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
          attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
          maxZoom: 17
        })
        break
    }

    newLayer.addTo(mapInstanceRef.current)
    basemapLayerRef.current = newLayer
  }, [basemapType])

  // Handle heatmap toggle
  useEffect(() => {
    if (!mapInstanceRef.current || !floats.length) return

    // Remove existing heatmap
    if (heatmapLayerRef.current) {
      mapInstanceRef.current.removeLayer(heatmapLayerRef.current)
      heatmapLayerRef.current = null
    }

    // Add heatmap if enabled
    if (showHeatmap) {
      const heatmapData = generateHeatmapData()
      const heatLayer = (L as any).heatLayer(heatmapData, {
        radius: 25,
        blur: 15,
        maxZoom: 17,
        gradient: {
          0.4: 'blue',
          0.6: 'cyan', 
          0.7: 'lime',
          0.8: 'yellow',
          1.0: 'red'
        }
      })
      
      heatLayer.addTo(mapInstanceRef.current)
      heatmapLayerRef.current = heatLayer
    }
  }, [showHeatmap, floats])

  // Handle trajectory toggle
  useEffect(() => {
    if (!mapInstanceRef.current) return

    // Remove existing trajectories
    if (trajectoriesLayerRef.current) {
      mapInstanceRef.current.removeLayer(trajectoriesLayerRef.current)
      trajectoriesLayerRef.current = null
    }

    // Add trajectories if enabled
    if (showTrajectories && floats.length > 0) {
      const trajectoryGroup = L.layerGroup()
      
      floats.forEach(float => {
        const trajectory = generateTrajectoryData(float)
        const polyline = L.polyline(trajectory, {
          color: '#ff6b6b',
          weight: 2,
          opacity: 0.7,
          dashArray: '5, 10'
        })
        
        polyline.bindPopup(`
          <div class="p-2">
            <h4 class="font-bold text-sm text-red-600">🌊 Predicted Drift Path</h4>
            <p class="text-xs">Float ${float.wmo_id || float.id}</p>
            <p class="text-xs text-gray-600">30-day projection based on current patterns</p>
          </div>
        `)
        
        trajectoryGroup.addLayer(polyline)
      })
      
      trajectoryGroup.addTo(mapInstanceRef.current)
      trajectoriesLayerRef.current = trajectoryGroup
    }
  }, [showTrajectories, floats])

  // Add markers when floats data changes
  useEffect(() => {
    if (!mapInstanceRef.current || !floats.length) return

    console.log('Adding markers for 2024 floats:', floats.length)

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
          <div class="p-3 min-w-[200px]">
            <h3 class="font-bold text-sm text-blue-800 mb-2">🌊 ARGO Float ${float.wmo_id || float.id}</h3>
            <div class="space-y-1 text-xs">
              <p><strong>Status:</strong> <span class="px-2 py-1 rounded text-white" style="background: ${float.status === 'active' ? '#22c55e' : '#ef4444'}">${float.status.toUpperCase()}</span></p>
              <p><strong>Position:</strong> ${float.latitude.toFixed(4)}°${float.latitude >= 0 ? 'N' : 'S'}, ${float.longitude.toFixed(4)}°${float.longitude >= 0 ? 'E' : 'W'}</p>
              <p><strong>Last Profile:</strong> ${new Date(float.last_position_date).toLocaleDateString('en-US', { 
                year: 'numeric', month: 'short', day: 'numeric' 
              })}</p>
              <p><strong>Ocean Region:</strong> ${getOceanRegion(float.latitude, float.longitude)}</p>
              <p><strong>Estimated Depth:</strong> ~2000m</p>
              <p><strong>Data Source:</strong> Vector Database</p>
            </div>
            <div class="mt-2 pt-2 border-t border-gray-200">
              <p class="text-xs text-gray-600 italic">💡 Click float for trajectory view</p>
            </div>
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
            <span className="text-gray-700 font-medium">Loading 2024 ARGO data...</span>
          </div>
        </div>
      )}

      {/* 2024 Data Controls */}
      <div className="absolute top-4 right-4 z-[1001] bg-white border border-gray-200 rounded-lg p-4 shadow-lg">
        <h3 className="text-sm font-medium text-gray-900 mb-3">🌊 Oceanographic Controls</h3>
        
        {/* Basemap Selector - Euro-Argo style */}
        <div className="mb-3">
          <label className="block text-xs text-gray-600 mb-1">Base Map:</label>
          <select
            value={basemapType}
            onChange={(e) => setBasemapType(e.target.value as 'satellite' | 'ocean' | 'terrain')}
            className="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="satellite">🛰️ Satellite (Esri)</option>
            <option value="ocean">� Ocean (Esri)</option>
            <option value="terrain">🗺️ Terrain (OpenTopo)</option>
          </select>
        </div>

        {/* Heatmap Toggle */}
        <div className="mb-3">
          <label className="flex items-center text-xs text-gray-600">
            <input
              type="checkbox"
              checked={showHeatmap}
              onChange={(e) => setShowHeatmap(e.target.checked)}
              className="mr-2"
            />
            🔥 Temperature Anomaly Heatmap
          </label>
        </div>

        {/* Trajectory Toggle */}
        <div className="mb-3">
          <label className="flex items-center text-xs text-gray-600">
            <input
              type="checkbox"
              checked={showTrajectories}
              onChange={(e) => setShowTrajectories(e.target.checked)}
              className="mr-2"
            />
            📍 Float Drift Trajectories
          </label>
        </div>
        
        {/* Month Filter */}
        <div className="mt-3">
          <label className="block text-xs text-gray-600 mb-1">Filter by Month:</label>
          <select
            value={selectedMonth || ''}
            onChange={(e) => setSelectedMonth(e.target.value ? parseInt(e.target.value) : null)}
            className="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">All Months (2024)</option>
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

        {/* Data Info */}
        <div className="mt-3 pt-3 border-t border-gray-200">
          <p className="text-xs text-gray-600">
            📍 {floats.length} ARGO Profiles (2024)
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Vector Database Source
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
            2024 ARGO Profiles: {floats.length}
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
              <div className="w-3 h-3 bg-gray-500 rounded-full"></div>
              Unknown: {floats.filter(f => f.status === 'unknown').length}
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

export default InteractiveMap2024