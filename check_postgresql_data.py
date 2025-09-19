#!/usr/bin/env python3
"""
Check PostgreSQL database with correct credentials
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import psycopg2
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime

# Database credentials from the attachment
DB_CONFIG = {
    'database': 'floatchat_db',
    'user': 'floatchat_user', 
    'password': 'floatchat_secure_2025',
    'host': 'localhost',
    'port': '5432'
}

def check_postgresql_data():
    """Check PostgreSQL database with correct credentials."""
    print("🔍 CHECKING POSTGRESQL DATABASE")
    print("=" * 50)
    print(f"Database: {DB_CONFIG['database']}")
    print(f"User: {DB_CONFIG['user']}")
    print(f"Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print()
    
    try:
        # Create connection string
        conn_string = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        engine = create_engine(conn_string)
        
        with engine.connect() as conn:
            print("✅ Connected to PostgreSQL successfully!")
            
            # Check what tables exist
            tables_query = """
                SELECT table_name, 
                       (SELECT COUNT(*) FROM information_schema.columns 
                        WHERE table_name = t.table_name AND table_schema = 'public') as column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """
            
            tables = conn.execute(text(tables_query)).fetchall()
            print(f"\n📊 Found {len(tables)} tables:")
            for table_name, col_count in tables:
                print(f"   📋 {table_name} ({col_count} columns)")
            
            # Check each ARGO-related table
            argo_tables = ['argo_floats', 'argo_profiles', 'argo_measurements']
            
            for table in argo_tables:
                if any(t[0] == table for t in tables):
                    print(f"\n🔍 Analyzing {table}:")
                    
                    try:
                        # Get row count
                        count_query = f"SELECT COUNT(*) FROM {table}"
                        total_rows = conn.execute(text(count_query)).scalar()
                        print(f"   📊 Total rows: {total_rows:,}")
                        
                        if total_rows > 0:
                            # Get column info
                            columns_query = f"""
                                SELECT column_name, data_type, is_nullable
                                FROM information_schema.columns 
                                WHERE table_name = '{table}' AND table_schema = 'public'
                                ORDER BY ordinal_position;
                            """
                            columns = conn.execute(text(columns_query)).fetchall()
                            print(f"   📋 Columns: {[col[0] for col in columns]}")
                            
                            # Try to find date columns
                            date_columns = [col[0] for col in columns if 'date' in col[0].lower() or 'time' in col[0].lower()]
                            if date_columns:
                                print(f"   📅 Date columns: {date_columns}")
                                
                                # Check date range for the first date column
                                date_col = date_columns[0]
                                try:
                                    date_range_query = f"""
                                        SELECT MIN({date_col}) as earliest,
                                               MAX({date_col}) as latest,
                                               COUNT(DISTINCT {date_col}) as unique_dates
                                        FROM {table}
                                        WHERE {date_col} IS NOT NULL
                                    """
                                    date_result = conn.execute(text(date_range_query)).fetchone()
                                    print(f"   📅 Date range ({date_col}): {date_result[0]} to {date_result[1]}")
                                    print(f"   📅 Unique dates: {date_result[2]:,}")
                                    
                                    # Check year distribution
                                    year_query = f"""
                                        SELECT EXTRACT(YEAR FROM {date_col}) as year,
                                               COUNT(*) as count
                                        FROM {table}
                                        WHERE {date_col} IS NOT NULL
                                        GROUP BY EXTRACT(YEAR FROM {date_col})
                                        ORDER BY year;
                                    """
                                    year_results = conn.execute(text(year_query)).fetchall()
                                    print(f"   📊 Year distribution:")
                                    for year, count in year_results:
                                        print(f"     {int(year)}: {count:,} records")
                                    
                                    # Check for 2024 data specifically
                                    count_2024 = conn.execute(text(f"""
                                        SELECT COUNT(*) FROM {table} 
                                        WHERE EXTRACT(YEAR FROM {date_col}) = 2024
                                    """)).scalar()
                                    print(f"   🎯 2024 data: {count_2024:,} records")
                                    
                                    # Check for October 2024
                                    count_oct_2024 = conn.execute(text(f"""
                                        SELECT COUNT(*) FROM {table} 
                                        WHERE EXTRACT(YEAR FROM {date_col}) = 2024 
                                        AND EXTRACT(MONTH FROM {date_col}) = 10
                                    """)).scalar()
                                    print(f"   🎯 October 2024: {count_oct_2024:,} records")
                                    
                                except Exception as e:
                                    print(f"   ❌ Date analysis error: {e}")
                            
                            # Sample some data
                            try:
                                sample_query = f"SELECT * FROM {table} LIMIT 3"
                                sample_results = conn.execute(text(sample_query)).fetchall()
                                if sample_results:
                                    print(f"   📄 Sample record columns: {list(sample_results[0].keys())}")
                            except Exception as e:
                                print(f"   ❌ Sample query error: {e}")
                        
                    except Exception as e:
                        print(f"   ❌ Error analyzing {table}: {e}")
                else:
                    print(f"\n❌ Table {table} not found")
            
            # Check for any processing logs or status tables
            print(f"\n🔍 Checking for processing logs:")
            log_tables = ['processing_logs', 'data_quality', 'etl_status', 'import_status']
            
            for log_table in log_tables:
                if any(t[0] == log_table for t in tables):
                    try:
                        count = conn.execute(text(f"SELECT COUNT(*) FROM {log_table}")).scalar()
                        print(f"   📋 {log_table}: {count:,} records")
                        
                        # Get recent logs
                        recent_logs = conn.execute(text(f"SELECT * FROM {log_table} ORDER BY id DESC LIMIT 3")).fetchall()
                        if recent_logs:
                            print(f"     Recent entries: {len(recent_logs)}")
                            
                    except Exception as e:
                        print(f"   ❌ {log_table} error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        print(f"   This might mean:")
        print(f"   1. PostgreSQL server is not running")
        print(f"   2. Database 'floatchat_db' doesn't exist")
        print(f"   3. User 'floatchat_user' doesn't have access")
        print(f"   4. Password is incorrect")
        return False

def check_database_server():
    """Check if PostgreSQL server is running."""
    print(f"\n🔍 CHECKING POSTGRESQL SERVER STATUS")
    print("=" * 50)
    
    try:
        # Try to connect to default postgres database
        basic_conn_string = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/postgres"
        engine = create_engine(basic_conn_string)
        
        with engine.connect() as conn:
            print("✅ PostgreSQL server is running!")
            
            # Check if our database exists
            db_check_query = """
                SELECT datname FROM pg_database 
                WHERE datname = 'floatchat_db';
            """
            result = conn.execute(text(db_check_query)).fetchone()
            
            if result:
                print("✅ Database 'floatchat_db' exists!")
            else:
                print("❌ Database 'floatchat_db' does not exist!")
                
                # List available databases
                list_db_query = "SELECT datname FROM pg_database WHERE datistemplate = false;"
                databases = conn.execute(text(list_db_query)).fetchall()
                print(f"   Available databases: {[db[0] for db in databases]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Server connection error: {e}")
        return False

def main():
    """Run PostgreSQL data check."""
    print("🔍 POSTGRESQL DATA VERIFICATION")
    print("=" * 70)
    print(f"Checking if ARGO data is safely stored in PostgreSQL...")
    print()
    
    # First check if server is running
    server_ok = check_database_server()
    
    if server_ok:
        # Then check our specific database
        data_ok = check_postgresql_data()
        
        print(f"\n📊 POSTGRESQL STATUS SUMMARY")
        print("=" * 40)
        print(f"Server Status: {'✅ RUNNING' if server_ok else '❌ NOT RUNNING'}")
        print(f"Data Status: {'✅ ACCESSIBLE' if data_ok else '❌ ISSUES FOUND'}")
        
        if data_ok:
            print(f"\n🎉 POSTGRESQL DATA IS SAFE!")
            print("Your ARGO data appears to be properly stored in PostgreSQL.")
        else:
            print(f"\n⚠️ POSTGRESQL DATA ISSUES DETECTED!")
            print("The data may not be properly loaded or accessible.")
    else:
        print(f"\n❌ POSTGRESQL SERVER NOT ACCESSIBLE!")
        print("Need to start PostgreSQL server or check connection settings.")

if __name__ == "__main__":
    main()