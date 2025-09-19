'use client';

import React, { useState, useEffect } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Line, Bar, Pie, Doughnut } from 'react-chartjs-2';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Download, 
  FileText, 
  Database, 
  TrendingUp, 
  Globe, 
  Thermometer, 
  Droplets,
  Activity,
  Calendar,
  MapPin,
  BarChart3,
  PieChart,
  LineChart,
  RefreshCw
} from 'lucide-react';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

interface DashboardData {
  overview: {
    totalFloats: number;
    totalProfiles: number;
    totalMeasurements: number;
    activeFloats: number;
    dataQualityScore: number;
    lastUpdated: string;
  };
  temporal: {
    yearlyProfiles: Array<{ year: number; profiles: number; floats: number }>;
    monthlyTrends: Array<{ month: string; temperature: number; salinity: number }>;
    deploymentTimeline: Array<{ date: string; deployed: number; cumulative: number }>;
  };
  geographic: {
    regions: Array<{ region: string; profiles: number; percentage: number }>;
    depthDistribution: Array<{ range: string; count: number }>;
    coordinates: Array<{ lat: number; lon: number; count: number }>;
  };
  environmental: {
    temperatureStats: { min: number; max: number; avg: number; std: number };
    salinityStats: { min: number; max: number; avg: number; std: number };
    pressureStats: { min: number; max: number; avg: number; std: number };
    qualityMetrics: Array<{ parameter: string; good: number; questionable: number; bad: number }>;
  };
}

const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Mock data for demonstration (replace with real API calls)
  const mockData: DashboardData = {
    overview: {
      totalFloats: 4125,
      totalProfiles: 2847392,
      totalMeasurements: 45783472,
      activeFloats: 3847,
      dataQualityScore: 94.7,
      lastUpdated: new Date().toISOString()
    },
    temporal: {
      yearlyProfiles: [
        { year: 2020, profiles: 285743, floats: 3200 },
        { year: 2021, profiles: 298456, floats: 3350 },
        { year: 2022, profiles: 312789, floats: 3500 },
        { year: 2023, profiles: 327891, floats: 3650 },
        { year: 2024, profiles: 342156, floats: 3800 },
        { year: 2025, profiles: 89357, floats: 3847 }
      ],
      monthlyTrends: [
        { month: 'Jan', temperature: 15.2, salinity: 34.8 },
        { month: 'Feb', temperature: 14.9, salinity: 34.9 },
        { month: 'Mar', temperature: 16.1, salinity: 34.7 },
        { month: 'Apr', temperature: 17.8, salinity: 34.6 },
        { month: 'May', temperature: 19.4, salinity: 34.5 },
        { month: 'Jun', temperature: 21.2, salinity: 34.4 },
        { month: 'Jul', temperature: 22.8, salinity: 34.3 },
        { month: 'Aug', temperature: 23.1, salinity: 34.2 },
        { month: 'Sep', temperature: 21.9, salinity: 34.4 },
        { month: 'Oct', temperature: 19.7, salinity: 34.6 },
        { month: 'Nov', temperature: 17.3, salinity: 34.7 },
        { month: 'Dec', temperature: 15.8, salinity: 34.8 }
      ],
      deploymentTimeline: [
        { date: '2020-01', deployed: 145, cumulative: 2845 },
        { date: '2020-07', deployed: 89, cumulative: 2934 },
        { date: '2021-01', deployed: 156, cumulative: 3090 },
        { date: '2021-07', deployed: 134, cumulative: 3224 },
        { date: '2022-01', deployed: 167, cumulative: 3391 },
        { date: '2022-07', deployed: 123, cumulative: 3514 },
        { date: '2023-01', deployed: 145, cumulative: 3659 },
        { date: '2023-07', deployed: 112, cumulative: 3771 },
        { date: '2024-01', deployed: 98, cumulative: 3869 },
        { date: '2024-07', deployed: 76, cumulative: 3945 }
      ]
    },
    geographic: {
      regions: [
        { region: 'North Pacific', profiles: 847392, percentage: 29.7 },
        { region: 'North Atlantic', profiles: 623847, percentage: 21.9 },
        { region: 'South Pacific', profiles: 456789, percentage: 16.0 },
        { region: 'South Atlantic', profiles: 389456, percentage: 13.7 },
        { region: 'Indian Ocean', profiles: 298567, percentage: 10.5 },
        { region: 'Southern Ocean', profiles: 231341, percentage: 8.1 }
      ],
      depthDistribution: [
        { range: '0-200m', count: 1256789 },
        { range: '200-500m', count: 987654 },
        { range: '500-1000m', count: 756432 },
        { range: '1000-1500m', count: 543210 },
        { range: '1500-2000m', count: 345678 },
        { range: '2000m+', count: 234567 }
      ],
      coordinates: [] // This would be populated with actual lat/lon data
    },
    environmental: {
      temperatureStats: { min: -2.1, max: 31.4, avg: 15.7, std: 8.3 },
      salinityStats: { min: 30.2, max: 37.8, avg: 34.6, std: 1.2 },
      pressureStats: { min: 0.1, max: 2087.4, avg: 567.8, std: 423.1 },
      qualityMetrics: [
        { parameter: 'Temperature', good: 94.7, questionable: 4.1, bad: 1.2 },
        { parameter: 'Salinity', good: 92.3, questionable: 6.2, bad: 1.5 },
        { parameter: 'Pressure', good: 96.8, questionable: 2.9, bad: 0.3 },
        { parameter: 'Oxygen', good: 89.1, questionable: 8.7, bad: 2.2 }
      ]
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/dashboard/data');
      if (!response.ok) {
        throw new Error('Failed to fetch dashboard data');
      }
      const dashboardData = await response.json();
      setData(dashboardData);
    } catch (err) {
      setError('Failed to load dashboard data');
      console.error('Dashboard data loading error:', err);
      // Fallback to mock data if API fails
      setData(mockData);
    } finally {
      setLoading(false);
    }
  };

  const refreshData = async () => {
    setRefreshing(true);
    await loadDashboardData();
    setRefreshing(false);
  };

  const exportData = async (format: 'csv' | 'json' | 'pdf') => {
    if (!data) return;
    
    try {
      if (format === 'csv') {
        const response = await fetch('/api/dashboard/data?format=csv');
        const csvContent = await response.text();
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `argo-dashboard-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else if (format === 'json') {
        const response = await fetch('/api/dashboard/data?format=export');
        const jsonData = await response.json();
        const dataStr = JSON.stringify(jsonData, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `argo-dashboard-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else if (format === 'pdf') {
        // For PDF, we'll create a simple report
        console.log('PDF export would be implemented here with a library like jsPDF');
        alert('PDF export functionality would be implemented with a library like jsPDF');
      }
    } catch (error) {
      console.error('Export error:', error);
      alert('Failed to export data. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto text-blue-500" />
          <p className="text-gray-600">Loading dashboard data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="text-red-500 text-lg">⚠️ {error}</div>
          <Button onClick={loadDashboardData} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  // Chart configurations
  const yearlyProfilesChart = {
    data: {
      labels: data.temporal.yearlyProfiles.map(d => d.year.toString()),
      datasets: [
        {
          label: 'Profiles',
          data: data.temporal.yearlyProfiles.map(d => d.profiles),
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          yAxisID: 'y'
        },
        {
          label: 'Active Floats',
          data: data.temporal.yearlyProfiles.map(d => d.floats),
          borderColor: 'rgb(16, 185, 129)',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' as const },
        title: { display: true, text: 'ARGO Profiles & Float Deployment Over Time' }
      },
      scales: {
        y: { type: 'linear' as const, display: true, position: 'left' as const },
        y1: { type: 'linear' as const, display: true, position: 'right' as const, grid: { drawOnChartArea: false } }
      }
    }
  };

  const monthlyTrendsChart = {
    data: {
      labels: data.temporal.monthlyTrends.map(d => d.month),
      datasets: [
        {
          label: 'Temperature (°C)',
          data: data.temporal.monthlyTrends.map(d => d.temperature),
          borderColor: 'rgb(239, 68, 68)',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          yAxisID: 'y'
        },
        {
          label: 'Salinity (PSU)',
          data: data.temporal.monthlyTrends.map(d => d.salinity),
          borderColor: 'rgb(34, 197, 94)',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' as const },
        title: { display: true, text: 'Monthly Temperature & Salinity Trends' }
      },
      scales: {
        y: { type: 'linear' as const, display: true, position: 'left' as const },
        y1: { type: 'linear' as const, display: true, position: 'right' as const, grid: { drawOnChartArea: false } }
      }
    }
  };

  const regionDistributionChart = {
    data: {
      labels: data.geographic.regions.map(r => r.region),
      datasets: [{
        data: data.geographic.regions.map(r => r.profiles),
        backgroundColor: [
          'rgba(59, 130, 246, 0.8)',
          'rgba(16, 185, 129, 0.8)',
          'rgba(239, 68, 68, 0.8)',
          'rgba(245, 158, 11, 0.8)',
          'rgba(139, 92, 246, 0.8)',
          'rgba(236, 72, 153, 0.8)'
        ],
        borderWidth: 2,
        borderColor: '#fff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right' as const },
        title: { display: true, text: 'Regional Profile Distribution' }
      }
    }
  };

  const depthDistributionChart = {
    data: {
      labels: data.geographic.depthDistribution.map(d => d.range),
      datasets: [{
        label: 'Measurements',
        data: data.geographic.depthDistribution.map(d => d.count),
        backgroundColor: 'rgba(59, 130, 246, 0.8)',
        borderColor: 'rgb(59, 130, 246)',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        title: { display: true, text: 'Depth Distribution of Measurements' }
      },
      scales: {
        y: { beginAtZero: true }
      }
    }
  };

  return (
    <div className="h-full w-full flex flex-col bg-gray-50 overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 p-3 bg-white border-b border-gray-200 shadow-sm">
        <div className="flex items-center justify-between min-w-0">
          <div className="min-w-0 flex-1">
            <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2 truncate">
              <BarChart3 className="h-5 w-5 text-blue-500 flex-shrink-0" />
              ARGO Analytics Dashboard
            </h2>
            <p className="text-xs text-gray-600 mt-1 truncate">
              Last updated: {new Date(data.overview.lastUpdated).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0 ml-4">
            <Button 
              onClick={refreshData} 
              variant="outline" 
              size="sm"
              disabled={refreshing}
              className="hidden sm:flex"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <div className="flex gap-1">
              <Button onClick={() => exportData('csv')} variant="outline" size="sm" className="px-2">
                <Download className="h-3 w-3" />
                <span className="hidden sm:inline ml-1">CSV</span>
              </Button>
              <Button onClick={() => exportData('json')} variant="outline" size="sm" className="px-2">
                <Download className="h-3 w-3" />
                <span className="hidden sm:inline ml-1">JSON</span>
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full overflow-auto p-3">
          <Tabs defaultValue="overview" className="h-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="temporal">Temporal</TabsTrigger>
            <TabsTrigger value="geographic">Geographic</TabsTrigger>
            <TabsTrigger value="environmental">Environmental</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-3 mt-4">
            {/* Overview Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <Card className="min-w-0">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-gray-900 truncate">Total Floats</CardTitle>
                  <Database className="h-4 w-4 text-blue-500 flex-shrink-0" />
                </CardHeader>
                <CardContent>
                  <div className="text-xl font-bold text-gray-900">{data.overview.totalFloats.toLocaleString()}</div>
                  <Badge variant="secondary" className="mt-1 text-xs">
                    {data.overview.activeFloats} active
                  </Badge>
                </CardContent>
              </Card>

              <Card className="min-w-0">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-gray-900 truncate">Profiles</CardTitle>
                  <Activity className="h-4 w-4 text-green-500 flex-shrink-0" />
                </CardHeader>
                <CardContent>
                  <div className="text-xl font-bold text-gray-900">{data.overview.totalProfiles.toLocaleString()}</div>
                  <p className="text-xs text-gray-600 mt-1 truncate">Temperature & Salinity</p>
                </CardContent>
              </Card>

              <Card className="min-w-0">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-gray-900 truncate">Measurements</CardTitle>
                  <TrendingUp className="h-4 w-4 text-purple-500 flex-shrink-0" />
                </CardHeader>
                <CardContent>
                  <div className="text-xl font-bold text-gray-900">{data.overview.totalMeasurements.toLocaleString()}</div>
                  <p className="text-xs text-gray-600 mt-1 truncate">All parameters</p>
                </CardContent>
              </Card>

              <Card className="min-w-0">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-gray-900 truncate">Data Quality</CardTitle>
                  <Activity className="h-4 w-4 text-green-500 flex-shrink-0" />
                </CardHeader>
                <CardContent>
                  <div className="text-xl font-bold text-gray-900">{data.overview.dataQualityScore}%</div>
                  <Badge variant="default" className="mt-1 text-xs">Excellent</Badge>
                </CardContent>
              </Card>

              <Card className="min-w-0">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-gray-900 truncate">Temperature</CardTitle>
                  <Thermometer className="h-4 w-4 text-red-500 flex-shrink-0" />
                </CardHeader>
                <CardContent>
                  <div className="text-xl font-bold text-gray-900">{data.environmental.temperatureStats.avg.toFixed(1)}°C</div>
                  <p className="text-xs text-gray-600 mt-1 truncate">Global average</p>
                </CardContent>
              </Card>

              <Card className="min-w-0">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-gray-900 truncate">Salinity</CardTitle>
                  <Droplets className="h-4 w-4 text-blue-500 flex-shrink-0" />
                </CardHeader>
                <CardContent>
                  <div className="text-xl font-bold text-gray-900">{data.environmental.salinityStats.avg.toFixed(1)} PSU</div>
                  <p className="text-xs text-gray-600 mt-1 truncate">Global average</p>
                </CardContent>
              </Card>
            </div>

            {/* Quick Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <Card className="min-w-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-gray-900 text-base">
                    <LineChart className="h-4 w-4 flex-shrink-0" />
                    Yearly Trends
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-48 w-full">
                    <Line data={yearlyProfilesChart.data} options={{...yearlyProfilesChart.options, maintainAspectRatio: false, responsive: true}} />
                  </div>
                </CardContent>
              </Card>

              <Card className="min-w-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-gray-900 text-base">
                    <PieChart className="h-4 w-4 flex-shrink-0" />
                    Regional Distribution
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-48 w-full">
                    <Doughnut data={regionDistributionChart.data} options={{...regionDistributionChart.options, maintainAspectRatio: false, responsive: true}} />
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="temporal" className="space-y-3 mt-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <Card className="min-w-0">
                <CardHeader>
                  <CardTitle className="text-gray-900 text-base">Profiles & Floats Timeline</CardTitle>
                  <CardDescription className="text-sm">Annual deployment and data collection trends</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-48 w-full">
                    <Line data={yearlyProfilesChart.data} options={{...yearlyProfilesChart.options, maintainAspectRatio: false, responsive: true}} />
                  </div>
                </CardContent>
              </Card>

              <Card className="min-w-0">
                <CardHeader>
                  <CardTitle className="text-gray-900 text-base">Monthly Environmental Trends</CardTitle>
                  <CardDescription className="text-sm">Temperature and salinity seasonal patterns</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-48 w-full">
                    <Line data={monthlyTrendsChart.data} options={{...monthlyTrendsChart.options, maintainAspectRatio: false, responsive: true}} />
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="min-w-0">
              <CardHeader>
                <CardTitle className="text-gray-900 text-base">Float Deployment Timeline</CardTitle>
                <CardDescription className="text-sm">Historical float deployment schedule</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-48 w-full">
                  <Bar 
                    data={{
                      labels: data.temporal.deploymentTimeline.map(d => d.date),
                      datasets: [{
                        label: 'Floats Deployed',
                        data: data.temporal.deploymentTimeline.map(d => d.deployed),
                        backgroundColor: 'rgba(59, 130, 246, 0.8)'
                      }]
                    }}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: { display: false },
                        title: { display: true, text: 'Float Deployments by Period' }
                      }
                    }}
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="geographic" className="space-y-3 mt-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <Card className="min-w-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-gray-900 text-base">
                    <Globe className="h-4 w-4 flex-shrink-0" />
                    Ocean Basin Coverage
                  </CardTitle>
                  <CardDescription className="text-sm">Profile distribution across major ocean regions</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-48 w-full">
                    <Pie data={regionDistributionChart.data} options={{...regionDistributionChart.options, maintainAspectRatio: false, responsive: true}} />
                  </div>
                </CardContent>
              </Card>

              <Card className="min-w-0">
                <CardHeader>
                  <CardTitle className="text-gray-900 text-base">Depth Distribution</CardTitle>
                  <CardDescription className="text-sm">Measurement distribution by depth ranges</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-48 w-full">
                    <Bar data={depthDistributionChart.data} options={{...depthDistributionChart.options, maintainAspectRatio: false, responsive: true}} />
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="min-w-0">
              <CardHeader>
                <CardTitle className="text-gray-900 text-base">Regional Statistics</CardTitle>
                <CardDescription className="text-sm">Detailed breakdown by ocean region</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {data.geographic.regions.map((region, index) => (
                    <div key={region.region} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <div 
                          className="w-3 h-3 rounded-full flex-shrink-0"
                          style={{ backgroundColor: regionDistributionChart.data.datasets[0].backgroundColor[index] }}
                        />
                        <span className="font-medium text-gray-900 text-sm truncate">{region.region}</span>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div className="text-sm font-bold text-gray-900">{region.profiles.toLocaleString()}</div>
                        <div className="text-xs text-gray-600">{region.percentage}%</div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="environmental" className="space-y-3 mt-4">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              <Card className="min-w-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-gray-900 text-base">
                    <Thermometer className="h-4 w-4 text-red-500 flex-shrink-0" />
                    Temperature Statistics
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Minimum:</span>
                      <span className="font-mono">{data.environmental.temperatureStats.min.toFixed(1)}°C</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Maximum:</span>
                      <span className="font-mono">{data.environmental.temperatureStats.max.toFixed(1)}°C</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Average:</span>
                      <span className="font-mono">{data.environmental.temperatureStats.avg.toFixed(1)}°C</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Std Dev:</span>
                      <span className="font-mono">±{data.environmental.temperatureStats.std.toFixed(1)}°C</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="min-w-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-gray-900 text-base">
                    <Droplets className="h-4 w-4 text-blue-500 flex-shrink-0" />
                    Salinity Statistics
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Minimum:</span>
                      <span className="font-mono">{data.environmental.salinityStats.min.toFixed(1)} PSU</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Maximum:</span>
                      <span className="font-mono">{data.environmental.salinityStats.max.toFixed(1)} PSU</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Average:</span>
                      <span className="font-mono">{data.environmental.salinityStats.avg.toFixed(1)} PSU</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Std Dev:</span>
                      <span className="font-mono">±{data.environmental.salinityStats.std.toFixed(1)} PSU</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="min-w-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-gray-900 text-base">
                    <Activity className="h-4 w-4 text-purple-500 flex-shrink-0" />
                    Pressure Statistics
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Minimum:</span>
                      <span className="font-mono">{data.environmental.pressureStats.min.toFixed(1)} dbar</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Maximum:</span>
                      <span className="font-mono">{data.environmental.pressureStats.max.toFixed(1)} dbar</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Average:</span>
                      <span className="font-mono">{data.environmental.pressureStats.avg.toFixed(1)} dbar</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Std Dev:</span>
                      <span className="font-mono">±{data.environmental.pressureStats.std.toFixed(1)} dbar</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="min-w-0">
              <CardHeader>
                <CardTitle className="text-gray-900 text-base">Data Quality Metrics</CardTitle>
                <CardDescription className="text-sm">Quality control flags for each parameter</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {data.environmental.qualityMetrics.map((metric) => (
                    <div key={metric.parameter} className="min-w-0">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-gray-900 text-sm truncate flex-1">{metric.parameter}</span>
                        <span className="text-xs text-gray-600 flex-shrink-0 ml-2">
                          {metric.good.toFixed(1)}% good
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div className="flex h-2 rounded-full overflow-hidden">
                          <div 
                            className="bg-green-500"
                            style={{ width: `${metric.good}%` }}
                          />
                          <div 
                            className="bg-yellow-500"
                            style={{ width: `${metric.questionable}%` }}
                          />
                          <div 
                            className="bg-red-500"
                            style={{ width: `${metric.bad}%` }}
                          />
                        </div>
                      </div>
                      <div className="flex justify-between text-xs text-gray-600 mt-1">
                        <span>Good: {metric.good}%</span>
                        <span>Quest: {metric.questionable}%</span>
                        <span>Bad: {metric.bad}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;