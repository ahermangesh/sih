import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    // Mock dashboard data (in real implementation, this would fetch from database)
    const dashboardData = {
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
        coordinates: []
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

    // Get query parameters for filtering
    const { searchParams } = new URL(request.url);
    const format = searchParams.get('format');
    
    if (format === 'csv') {
      // Convert data to CSV format
      let csvContent = 'Date,Floats,Profiles,Quality_Score\n';
      dashboardData.temporal.yearlyProfiles.forEach(item => {
        csvContent += `${item.year},${item.floats},${item.profiles},${dashboardData.overview.dataQualityScore}\n`;
      });
      
      return new NextResponse(csvContent, {
        headers: {
          'Content-Type': 'text/csv',
          'Content-Disposition': `attachment; filename="argo-dashboard-${new Date().toISOString().split('T')[0]}.csv"`
        }
      });
    }
    
    if (format === 'export') {
      // Enhanced export format with all data
      const exportData = {
        ...dashboardData,
        metadata: {
          exportDate: new Date().toISOString(),
          version: '1.0.0',
          totalRecords: dashboardData.overview.totalProfiles
        }
      };
      
      return NextResponse.json(exportData, {
        headers: {
          'Content-Disposition': `attachment; filename="argo-dashboard-full-${new Date().toISOString().split('T')[0]}.json"`
        }
      });
    }
    
    // Regular API response
    return NextResponse.json(dashboardData);
    
  } catch (error) {
    console.error('Dashboard API error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch dashboard data' },
      { status: 500 }
    );
  }
}