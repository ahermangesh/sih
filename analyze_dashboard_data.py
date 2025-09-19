#!/usr/bin/env python3
"""
Dashboard Data Analysis Script
Analyzes ARGO data to determine what metrics and visualizations to include in the dashboard
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_sync_session, init_database
from sqlalchemy import text
import asyncio

async def main():
    """Main analysis function"""
    # Initialize database first
    await init_database()
    
    # Get sync session for analysis
    session = get_sync_session()
    
    try:
        print('=== FLOATCHAT DASHBOARD DATA ANALYSIS ===\n')
        
        # 1. Check available tables
        print('📋 AVAILABLE TABLES:')
        result = session.execute(text("""
            SELECT table_name, 
                   (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        tables = result.fetchall()
        
        total_tables = 0
        for table_name, col_count in tables:
            print(f'   • {table_name} ({col_count} columns)')
            total_tables += 1
        
        if total_tables == 0:
            print('   ⚠️  No tables found!')
            return
        
        # 2. ARGO Profiles Analysis
        print('\n🌊 ARGO PROFILES ANALYSIS:')
        
        # Check if argo_profiles exists
        result = session.execute(text("SELECT COUNT(*) FROM argo_profiles"))
        total_profiles = result.fetchone()[0]
        print(f'   Total Profiles: {total_profiles:,}')
        
        if total_profiles > 0:
            # Date range analysis
            result = session.execute(text("""
                SELECT 
                    MIN(profile_date) as earliest_date,
                    MAX(profile_date) as latest_date,
                    COUNT(DISTINCT EXTRACT(YEAR FROM profile_date)) as years_span
                FROM argo_profiles 
                WHERE profile_date IS NOT NULL
            """))
            date_info = result.fetchone()
            print(f'   Date Range: {date_info[0]} to {date_info[1]}')
            print(f'   Years Covered: {date_info[2]} years')
            
            # Yearly breakdown
            result = session.execute(text("""
                SELECT 
                    EXTRACT(YEAR FROM profile_date) as year, 
                    COUNT(*) as profiles,
                    COUNT(DISTINCT wmo_id) as unique_floats
                FROM argo_profiles 
                WHERE profile_date IS NOT NULL
                GROUP BY EXTRACT(YEAR FROM profile_date) 
                ORDER BY year
            """))
            yearly_data = result.fetchall()
            print(f'\n   📅 YEARLY BREAKDOWN:')
            for year, profiles, floats in yearly_data:
                print(f'      {int(year)}: {profiles:,} profiles from {floats} floats')
            
            # Geographic coverage
            result = session.execute(text("""
                SELECT 
                    MIN(latitude) as min_lat, MAX(latitude) as max_lat,
                    MIN(longitude) as min_lon, MAX(longitude) as max_lon,
                    COUNT(DISTINCT ROUND(latitude::numeric, 1) || ',' || ROUND(longitude::numeric, 1)) as unique_locations
                FROM argo_profiles 
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            """))
            geo_stats = result.fetchone()
            print(f'\n   🌍 GEOGRAPHIC COVERAGE:')
            print(f'      Latitude: {geo_stats[0]:.2f}° to {geo_stats[1]:.2f}°')
            print(f'      Longitude: {geo_stats[2]:.2f}° to {geo_stats[3]:.2f}°')
            print(f'      Unique Locations: {geo_stats[4]:,}')
        
        # 3. ARGO Measurements Analysis
        print('\n🌡️  ARGO MEASUREMENTS ANALYSIS:')
        result = session.execute(text("SELECT COUNT(*) FROM argo_measurements"))
        total_measurements = result.fetchone()[0]
        print(f'   Total Measurements: {total_measurements:,}')
        
        if total_measurements > 0:
            # Temperature statistics
            result = session.execute(text("""
                SELECT 
                    MIN(temperature) as min_temp, 
                    MAX(temperature) as max_temp,
                    AVG(temperature) as avg_temp,
                    STDDEV(temperature) as std_temp,
                    COUNT(*) as temp_count
                FROM argo_measurements 
                WHERE temperature IS NOT NULL
            """))
            temp_stats = result.fetchone()
            print(f'   🌡️  Temperature Stats:')
            print(f'      Range: {temp_stats[0]:.2f}°C to {temp_stats[1]:.2f}°C')
            print(f'      Average: {temp_stats[2]:.2f}°C (±{temp_stats[3]:.2f}°C)')
            print(f'      Valid Records: {temp_stats[4]:,}')
            
            # Salinity statistics
            result = session.execute(text("""
                SELECT 
                    MIN(salinity) as min_sal, 
                    MAX(salinity) as max_sal,
                    AVG(salinity) as avg_sal,
                    STDDEV(salinity) as std_sal,
                    COUNT(*) as sal_count
                FROM argo_measurements 
                WHERE salinity IS NOT NULL
            """))
            sal_stats = result.fetchone()
            print(f'   🧂 Salinity Stats:')
            print(f'      Range: {sal_stats[0]:.2f} to {sal_stats[1]:.2f} PSU')
            print(f'      Average: {sal_stats[2]:.2f} PSU (±{sal_stats[3]:.2f} PSU)')
            print(f'      Valid Records: {sal_stats[4]:,}')
            
            # Depth analysis
            result = session.execute(text("""
                SELECT 
                    MIN(depth) as min_depth, 
                    MAX(depth) as max_depth,
                    AVG(depth) as avg_depth,
                    COUNT(*) as depth_count
                FROM argo_measurements 
                WHERE depth IS NOT NULL
            """))
            depth_stats = result.fetchone()
            print(f'   🌊 Depth Stats:')
            print(f'      Range: {depth_stats[0]:.1f}m to {depth_stats[1]:.1f}m')
            print(f'      Average: {depth_stats[2]:.1f}m')
            print(f'      Valid Records: {depth_stats[3]:,}')
        
        # 4. ARGO Floats Analysis
        print('\n🛟 ARGO FLOATS ANALYSIS:')
        result = session.execute(text("SELECT COUNT(*) FROM argo_floats"))
        total_floats = result.fetchone()[0]
        print(f'   Total Floats: {total_floats:,}')
        
        if total_floats > 0:
            # Active vs inactive floats
            result = session.execute(text("""
                SELECT 
                    status, 
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
                FROM argo_floats 
                GROUP BY status
            """))
            status_data = result.fetchall()
            print(f'   Status Breakdown:')
            for status, count, percentage in status_data:
                print(f'      {status}: {count:,} ({percentage}%)')
        
        # 5. Suggested Dashboard Metrics
        print('\n📊 SUGGESTED DASHBOARD METRICS:')
        print('   ✅ Time Series Charts:')
        print('      • Monthly/Yearly profile counts')
        print('      • Temperature trends over time')
        print('      • Salinity trends over time')
        print('      • Float deployment timeline')
        
        print('   ✅ Geographic Visualizations:')
        print('      • Global float distribution heatmap')
        print('      • Regional data density maps')
        print('      • Ocean basin coverage')
        
        print('   ✅ Statistical Summaries:')
        print('      • Real-time data overview cards')
        print('      • Temperature/Salinity histograms')
        print('      • Depth profile distributions')
        print('      • Float status pie charts')
        
        print('   ✅ Export Options:')
        print('      • CSV data exports')
        print('      • JSON API endpoints')
        print('      • Chart image downloads')
        print('      • PDF report generation')
        
        print('\n✨ DASHBOARD READY FOR IMPLEMENTATION!')
        
    except Exception as e:
        print(f'❌ Analysis Error: {e}')
        print(f'Error Type: {type(e).__name__}')
        
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(main())