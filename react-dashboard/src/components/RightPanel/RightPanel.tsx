import React, { useState, useEffect } from 'react';
import './RightPanel.css';

const RightPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'filters' | 'charts'>('filters');
  const [dailyData, setDailyData] = useState([
    { day: 'D1', occurrences: 120 },
    { day: 'D2', occurrences: 180 },
    { day: 'D3', occurrences: 240 },
    { day: 'D4', occurrences: 310 },
    { day: 'D5', occurrences: 435 },
    { day: 'D6', occurrences: 210 },
    { day: 'D7', occurrences: 260 }
  ]);

  // Simulate real-time data updates
  useEffect(() => {
    const interval = setInterval(() => {
      setDailyData(prevData => 
        prevData.map(item => ({
          ...item,
          occurrences: Math.max(50, item.occurrences + Math.floor((Math.random() - 0.5) * 40))
        }))
      );
    }, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, []);

  // Calculate SVG path and area
  const generatePath = () => {
    const width = 300;
    const height = 120;
    const padding = 20;
    const maxOccurrences = Math.max(...dailyData.map(d => d.occurrences));
    const minOccurrences = Math.min(...dailyData.map(d => d.occurrences));
    const range = maxOccurrences - minOccurrences || 1;

    const points = dailyData.map((item, index) => {
      const x = padding + (index * (width - 2 * padding)) / (dailyData.length - 1);
      const y = height - padding - ((item.occurrences - minOccurrences) / range) * (height - 2 * padding);
      return { x, y, occurrences: item.occurrences };
    });

    const pathData = points.reduce((acc, point, index) => {
      const command = index === 0 ? 'M' : 'L';
      return `${acc} ${command} ${point.x} ${point.y}`;
    }, '');

    const areaData = `${pathData} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`;

    return { pathData, areaData, points };
  };

  const { pathData, areaData, points } = generatePath();

  return (
    <div className="right-panel">
      <div className="panel-tabs">
        <button 
          className={`tab ${activeTab === 'filters' ? 'active' : ''}`}
          onClick={() => setActiveTab('filters')}
        >
          Filters
        </button>
        <button 
          className={`tab ${activeTab === 'charts' ? 'active' : ''}`}
          onClick={() => setActiveTab('charts')}
        >
          Charts
        </button>
      </div>

      {activeTab === 'filters' && (
        <div className="filters-section">
          {/* Stats Grid */}
          <div className="stats-grid">
            <div className="stats-header">
              <span className="header-item">Categories</span>
              <span className="header-item">Processed</span>
              <span className="header-item">Pending</span>
            </div>
            <div className="stat-row">
              <div className="stat-large">
                <span className="stat-number">627</span>
                <span className="stat-label">Entries</span>
              </div>
              <div className="stat-small">
                <span className="stat-number">$165</span>
                <span className="stat-label">Resolved</span>
              </div>
              <div className="stat-small">
                <span className="stat-number">35</span>
                <span className="stat-label">Pending</span>
              </div>
            </div>
            
            <div className="stats-header">
              <span className="header-item">Detections</span>
              <span className="header-item">Avg. Value</span>
              <span className="header-item">Index</span>
            </div>
            <div className="stat-row">
              <div className="stat-large">
                <span className="stat-number">442</span>
                <span className="stat-label">Detection</span>
              </div>
              <div className="stat-small">
                <span className="stat-number">$3.3</span>
                <span className="stat-label">Average Value</span>
              </div>
              <div className="stat-small">
                <span className="stat-number">2.5</span>
                <span className="stat-label">Detection Rate</span>
              </div>
            </div>
          </div>

          {/* Daily Occurrences Chart */}
          <div className="ocean-data-section">
            <h3>Daily Occurrences</h3>
            <div className="ocean-chart-container">
              <svg viewBox="0 0 300 120" className="ocean-chart">
                <defs>
                  <linearGradient id="occurrenceGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" style={{stopColor:'#4A90E2', stopOpacity:0.6}} />
                    <stop offset="100%" style={{stopColor:'#4A90E2', stopOpacity:0.1}} />
                  </linearGradient>
                  
                  {/* Grid pattern */}
                  <pattern id="grid" width="40" height="20" patternUnits="userSpaceOnUse">
                    <path d="M 40 0 L 0 0 0 20" fill="none" stroke="#f0f0f0" strokeWidth="1"/>
                  </pattern>
                </defs>
                
                {/* Grid background */}
                <rect width="100%" height="100%" fill="url(#grid)" opacity="0.5"/>
                
                {/* Y-axis labels */}
                <text x="10" y="25" fontSize="10" fill="#999" textAnchor="middle">400</text>
                <text x="10" y="45" fontSize="10" fill="#999" textAnchor="middle">300</text>
                <text x="10" y="65" fontSize="10" fill="#999" textAnchor="middle">200</text>
                <text x="10" y="85" fontSize="10" fill="#999" textAnchor="middle">100</text>
                <text x="10" y="105" fontSize="10" fill="#999" textAnchor="middle">0</text>
                
                {/* Area fill */}
                <path d={areaData} fill="url(#occurrenceGradient)"/>
                
                {/* Line path */}
                <path d={pathData} stroke="#4A90E2" strokeWidth="2" fill="none"/>
                
                {/* Data points */}
                {points.map((point, index) => (
                  <g key={index}>
                    <circle 
                      cx={point.x} 
                      cy={point.y} 
                      r="3" 
                      fill="#4A90E2"
                      className="data-point"
                    />
                    {/* Hover tooltip */}
                    <circle 
                      cx={point.x} 
                      cy={point.y} 
                      r="8" 
                      fill="transparent"
                      className="data-point-hover"
                    >
                      <title>{`${dailyData[index].day}: ${point.occurrences} occurrences`}</title>
                    </circle>
                  </g>
                ))}
                
                {/* X-axis labels */}
                {dailyData.map((item, index) => {
                  const x = 20 + (index * 260) / (dailyData.length - 1);
                  return (
                    <text key={item.day} x={x} y="115" fontSize="10" fill="#666" textAnchor="middle">
                      {item.day}
                    </text>
                  );
                })}
              </svg>
              
              {/* Live indicator */}
              <div className="live-indicator">
                <span className="live-dot"></span>
                <span>Live Data</span>
              </div>
            </div>
          </div>

          {/* Summary Section */}
          <div className="summary-section">
            <h3>Summary</h3>
            <div className="summary-cards">
              <div className="summary-card">
                <div className="card-icon">📊</div>
                <div className="card-content">
                  <span className="card-value">25.5 km</span>
                  <span className="card-label">Distance</span>
                </div>
              </div>
              
              <div className="summary-card primary">
                <div className="card-content">
                  <span className="card-value">25.4 km</span>
                  <span className="card-label">Depth</span>
                </div>
              </div>
              
              <div className="summary-card">
                <div className="card-content">
                  <span className="card-value">25.2 km</span>
                  <span className="card-label">Temperature</span>
                </div>
              </div>
              
              <div className="summary-card">
                <div className="card-content">
                  <span className="card-value">70.1 km</span>
                  <span className="card-label">Pressure</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'charts' && (
        <div className="charts-section">
          <div className="charts-content">
            <h3>Data Visualization</h3>
            <p>Advanced charts and analytics will be displayed here.</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default RightPanel;
