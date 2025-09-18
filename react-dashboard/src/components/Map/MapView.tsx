import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet';
import L from 'leaflet';
import './MapView.css';
import 'leaflet/dist/leaflet.css';

interface Float {
  id: string;
  lat: number;
  lng: number;
  temperature: number;
  salinity: number;
  depth: number;
  status: 'active' | 'inactive';
}

// Fix for default markers in React-Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// Custom icons for different float statuses
const activeFloatIcon = new L.Icon({
  iconUrl: 'data:image/svg+xml;base64,' + btoa(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 25 25" width="25" height="25">
      <circle cx="12.5" cy="12.5" r="8" fill="#00ff00" stroke="#fff" stroke-width="2"/>
      <circle cx="12.5" cy="12.5" r="4" fill="#ffffff"/>
    </svg>
  `),
  iconSize: [25, 25],
  iconAnchor: [12.5, 12.5],
  popupAnchor: [0, -12.5],
});

const inactiveFloatIcon = new L.Icon({
  iconUrl: 'data:image/svg+xml;base64,' + btoa(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 25 25" width="25" height="25">
      <circle cx="12.5" cy="12.5" r="8" fill="#ff4444" stroke="#fff" stroke-width="2"/>
      <circle cx="12.5" cy="12.5" r="4" fill="#ffffff"/>
    </svg>
  `),
  iconSize: [25, 25],
  iconAnchor: [12.5, 12.5],
  popupAnchor: [0, -12.5],
});

const MapView: React.FC = () => {
  const [showLegend, setShowLegend] = useState(false);

  // Sample float data for demonstration - Indian Ocean region with better distribution
  const floats: Float[] = [
    { id: 'F001', lat: 18.9750, lng: 72.8258, temperature: 28.5, salinity: 35.2, depth: 100, status: 'active' }, // Arabian Sea (Mumbai)
    { id: 'F002', lat: 13.0878, lng: 80.2785, temperature: 29.1, salinity: 35.8, depth: 150, status: 'active' }, // Bay of Bengal (Chennai)
    { id: 'F003', lat: 22.5675, lng: 88.3700, temperature: 27.8, salinity: 34.9, depth: 200, status: 'inactive' }, // Bay of Bengal (Kolkata)
    { id: 'F004', lat: 8.0883, lng: 77.0595, temperature: 26.3, salinity: 35.1, depth: 180, status: 'active' }, // Arabian Sea (Kerala)
    { id: 'F005', lat: 15.4909, lng: 73.8278, temperature: 28.9, salinity: 35.5, depth: 120, status: 'active' }, // Arabian Sea (Goa)
    { id: 'F006', lat: 11.0000, lng: 85.0000, temperature: 27.2, salinity: 35.0, depth: 140, status: 'active' }, // Central Bay of Bengal
    { id: 'F007', lat: 6.9271, lng: 79.8612, temperature: 28.7, salinity: 35.3, depth: 110, status: 'inactive' }, // Near Sri Lanka
    { id: 'F008', lat: 12.0000, lng: 68.0000, temperature: 29.5, salinity: 35.7, depth: 95, status: 'active' }, // Central Arabian Sea
    { id: 'F009', lat: 4.2105, lng: 73.5074, temperature: 28.1, salinity: 35.4, depth: 160, status: 'active' }, // Near Maldives
    { id: 'F010', lat: 16.0000, lng: 94.0000, temperature: 27.9, salinity: 34.8, depth: 130, status: 'inactive' }, // Andaman Sea
  ];

  return (
    <div className="map-view">
      <div className="map-header">
        <h2>Argo Float Locations - Indian Ocean Region</h2>
      </div>

      <div className="map-container">
        <MapContainer 
          center={[15.0, 80.0]}             // Centered on Indian Ocean
          zoom={4}                          // Wider view to show ocean context
          minZoom={3}                       // Allow more zoom out for ocean view
          maxZoom={10}                      // Reduce max zoom for cleaner appearance
          style={{ height: '90vh', width: '100%' }}
          className="leaflet-map"
          attributionControl={false}        // Disable attribution control
        >
          {/* Colorful physical map without labels */}
          <TileLayer
            attribution='&copy; <a href="https://www.esri.com/">Esri</a>'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          />
          
          {/* Add ocean bathymetry overlay for better ocean visualization */}
          <TileLayer
            attribution='Ocean Features'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}"
            opacity={0.7}
          />
          
          {/* Render Argo Float markers */}
          {floats.map((float) => (
            <Marker
              key={float.id}
              position={[float.lat, float.lng]}
              icon={float.status === 'active' ? activeFloatIcon : inactiveFloatIcon}
            >
              <Popup>
                <div className="float-popup">
                  <h3>Float {float.id}</h3>
                  <div className="float-data">
                    <p><strong>Status:</strong> <span className={float.status}>{float.status}</span></p>
                    <p><strong>Temperature:</strong> {float.temperature}°C</p>
                    <p><strong>Salinity:</strong> {float.salinity} PSU</p>
                    <p><strong>Depth:</strong> {float.depth}m</p>
                    <p><strong>Position:</strong> {float.lat.toFixed(4)}°N, {float.lng.toFixed(4)}°E</p>
                  </div>
                </div>
              </Popup>
              
              {/* Add a circle to show sensing range */}
              <Circle
                center={[float.lat, float.lng]}
                radius={float.status === 'active' ? 50000 : 25000} // 50km for active, 25km for inactive
                pathOptions={{
                  color: float.status === 'active' ? '#00ff00' : '#ff4444',
                  fillColor: float.status === 'active' ? '#00ff00' : '#ff4444',
                  fillOpacity: 0.1,
                  weight: 1,
                }}
              />
            </Marker>
          ))}
        </MapContainer>
      </div>

      {/* Legend Toggle Button */}
      <button 
        className="legend-toggle-btn"
        onClick={() => setShowLegend(!showLegend)}
        title="Toggle Legend"
      >
        ℹ️
      </button>

      {/* Map Legend - Conditionally Rendered */}
      {showLegend && (
        <div className="map-legend">
          <h4>Legend</h4>
          <div className="legend-item">
            <div className="legend-icon active-float"></div>
            <span>Active Float</span>
          </div>
          <div className="legend-item">
            <div className="legend-icon inactive-float"></div>
            <span>Inactive Float</span>
          </div>
          <div className="legend-item">
            <div className="legend-icon ocean"></div>
            <span>Ocean Coverage</span>
          </div>
        </div>
      )}
    </div>
  );
};
export default MapView;
