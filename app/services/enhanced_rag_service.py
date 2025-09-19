"""
Enhanced RAG Service with Temporal Query Support
Fixes the issue where temporal queries (like "October 2024") are not properly routed to PostgreSQL
"""

import re
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import structlog

from app.core.config import get_settings
from app.core.database import get_async_session
from app.services.nlu_service import NLUService, QueryAnalysis

logger = structlog.get_logger(__name__)


@dataclass 
class RAGResponse:
    """Complete response from RAG pipeline."""
    response: str
    confidence_score: float
    retrieved_contexts: List[Any] = field(default_factory=list)
    sql_query: Optional[str] = None
    query_results: Optional[List[Dict[str, Any]]] = None
    fact_check_results: Optional[Dict[str, Any]] = None
    generation_metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: int = 0


class RAGPipeline:
    """Base RAG pipeline class."""
    
    def __init__(self):
        pass
    
    async def initialize(self):
        """Initialize pipeline."""
        pass
    
    async def process_query(
        self,
        query: str,
        conversation_id: str = None,
        user_preferences: Dict[str, Any] = None,
        correlation_id: str = None
    ) -> RAGResponse:
        """Process query - to be implemented by subclasses."""
        return RAGResponse(
            response="Standard RAG not implemented",
            confidence_score=0.0,
            processing_time_ms=0
        )


class TemporalQueryDetector:
    """Detect temporal queries that should be routed to PostgreSQL."""
    
    def __init__(self):
        # Patterns for temporal expressions
        self.temporal_patterns = [
            # Year patterns
            r'\b(20\d{2})\b',  # 2020, 2021, etc.
            
            # Month-year patterns
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s*(20\d{2})\b',
            r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s*(20\d{2})\b',
            r'\b(20\d{2})[-/](0?[1-9]|1[0-2])\b',  # 2024-10, 2024/10
            
            # Recent time expressions
            r'\b(recent|latest|current|new|fresh|updated)\b',
            r'\b(last|past)\s+(year|month|week|day)s?\b',
            r'\b(this|current)\s+(year|month|week)\b',
            
            # Specific date expressions
            r'\b(today|yesterday|now)\b',
            r'\boctober\s*(20\d{2})?\b',  # October or October 2024
        ]
        
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.temporal_patterns]
    
    def is_temporal_query(self, query: str) -> bool:
        """Check if query contains temporal expressions."""
        for pattern in self.compiled_patterns:
            if pattern.search(query):
                return True
        return False
    
    def extract_temporal_info(self, query: str) -> Dict[str, Any]:
        """Extract temporal information from query."""
        temporal_info = {
            'year': None,
            'month': None,
            'is_recent': False,
            'date_range': None
        }
        
        # Extract year
        year_match = re.search(r'\b(20\d{2})\b', query)
        if year_match:
            temporal_info['year'] = int(year_match.group(1))
        
        # Extract month
        month_patterns = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
            'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        
        for month_name, month_num in month_patterns.items():
            if re.search(rf'\b{month_name}\b', query, re.IGNORECASE):
                temporal_info['month'] = month_num
                break
        
        # Check for recent indicators
        recent_patterns = ['recent', 'latest', 'current', 'new', 'fresh', 'updated', 'last', 'this']
        for pattern in recent_patterns:
            if re.search(rf'\b{pattern}\b', query, re.IGNORECASE):
                temporal_info['is_recent'] = True
                break
        
        # Build date range
        if temporal_info['year'] and temporal_info['month']:
            start_date = f"{temporal_info['year']}-{temporal_info['month']:02d}-01"
            if temporal_info['month'] == 12:
                end_date = f"{temporal_info['year'] + 1}-01-01"
            else:
                end_date = f"{temporal_info['year']}-{temporal_info['month'] + 1:02d}-01"
            temporal_info['date_range'] = (start_date, end_date)
        elif temporal_info['year']:
            temporal_info['date_range'] = (f"{temporal_info['year']}-01-01", f"{temporal_info['year'] + 1}-01-01")
        elif temporal_info['is_recent']:
            # Last 6 months
            now = datetime.now()
            six_months_ago = now - timedelta(days=180)
            temporal_info['date_range'] = (six_months_ago.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d'))
        
        return temporal_info


class PostgreSQLQueryExecutor:
    """Execute temporal queries directly on PostgreSQL."""
    
    def __init__(self):
        self.settings = get_settings()
        # Use correct database credentials
        self.db_config = {
            'database': 'floatchat_db',
            'user': 'floatchat_user',
            'password': 'floatchat_secure_2025',
            'host': 'localhost',
            'port': '5432'
        }
        self.engine = None
    
    async def initialize(self):
        """Initialize PostgreSQL connection."""
        try:
            conn_string = f"postgresql://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            self.engine = create_engine(conn_string)
            logger.info("PostgreSQL connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection: {e}")
            raise
    
    async def execute_temporal_query(self, query: str, temporal_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute temporal query against PostgreSQL."""
        try:
            if not self.engine:
                await self.initialize()
            
            # Build SQL query based on temporal info and user query
            sql_query = self._build_temporal_sql(query, temporal_info)
            
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_query))
                rows = result.fetchall()
                
                # Convert to list of dictionaries
                columns = result.keys()
                return [dict(zip(columns, row)) for row in rows]
        
        except Exception as e:
            logger.error(f"Error executing temporal query: {e}")
            return []
    
    def _determine_query_limit(self, query: str, temporal_info: Dict[str, Any]) -> int:
        """Determine appropriate limit based on query type and temporal scope."""
        
        # Analysis keywords suggest user wants comprehensive data
        analysis_keywords = ['compare', 'analysis', 'trend', 'pattern', 'all', 'complete', 'comprehensive']
        if any(keyword in query.lower() for keyword in analysis_keywords):
            # For analysis queries, allow more data
            if temporal_info.get('month'):
                # Monthly data - moderate limit
                return 500
            elif temporal_info.get('year'):
                # Yearly data - higher limit for comprehensive analysis
                return 1000
            else:
                # Multi-year analysis - very high limit
                return 2000
        
        # Specific data requests
        show_keywords = ['show', 'display', 'list', 'get']
        if any(keyword in query.lower() for keyword in show_keywords):
            # For display queries, reasonable limit
            if temporal_info.get('month'):
                return 300
            else:
                return 500
        
        # Data availability checks
        availability_keywords = ['available', 'have', 'exists', 'contains']
        if any(keyword in query.lower() for keyword in availability_keywords):
            # For availability checks, sample is sufficient
            return 100
        
        # Default limit
        return 250

    def _build_temporal_sql(self, query: str, temporal_info: Dict[str, Any]) -> str:
        """Build SQL query for temporal data retrieval with intelligent limits."""
        
        # Determine what data to query based on user request
        if any(word in query.lower() for word in ['profile', 'measurement', 'temperature', 'salinity']):
            base_table = 'argo_profiles'
            date_column = 'profile_date'
        elif any(word in query.lower() for word in ['float', 'deployment']):
            base_table = 'argo_floats'
            date_column = 'deployment_date'
        else:
            # Default to profiles for oceanographic data
            base_table = 'argo_profiles'
            date_column = 'profile_date'
        
        # Determine intelligent limit based on query type and temporal scope
        limit = self._determine_query_limit(query, temporal_info)
        
        # Build base query
        if base_table == 'argo_profiles':
            sql = f"""
                SELECT p.id, p.cycle_number, p.profile_date, p.latitude, p.longitude,
                       f.wmo_id, f.platform_type,
                       COUNT(m.id) as measurement_count,
                       MIN(m.temperature) as min_temp,
                       MAX(m.temperature) as max_temp,
                       MIN(m.salinity) as min_salinity,
                       MAX(m.salinity) as max_salinity,
                       MAX(m.pressure) as max_pressure
                FROM {base_table} p
                JOIN argo_floats f ON p.float_id = f.id
                LEFT JOIN argo_measurements m ON p.id = m.profile_id
            """
        else:
            sql = f"""
                SELECT f.id, f.wmo_id, f.platform_type, f.deployment_date,
                       f.deployment_latitude, f.deployment_longitude, f.status,
                       COUNT(p.id) as profile_count
                FROM {base_table} f
                LEFT JOIN argo_profiles p ON f.id = p.float_id
            """
        
        # Add temporal conditions
        where_conditions = []
        
        if temporal_info['date_range']:
            start_date, end_date = temporal_info['date_range']
            where_conditions.append(f"{date_column} >= '{start_date}' AND {date_column} < '{end_date}'")
        
        # Add geographic filters if mentioned
        if 'arabian sea' in query.lower():
            where_conditions.append("latitude BETWEEN 10 AND 25 AND longitude BETWEEN 50 AND 75")
        elif 'indian ocean' in query.lower():
            where_conditions.append("latitude BETWEEN -50 AND 30 AND longitude BETWEEN 30 AND 120")
        elif 'bay of bengal' in query.lower():
            where_conditions.append("latitude BETWEEN 5 AND 25 AND longitude BETWEEN 80 AND 100")
        
        # Add WHERE clause
        if where_conditions:
            sql += " WHERE " + " AND ".join(where_conditions)
        
        # Add GROUP BY for aggregated queries
        if base_table == 'argo_profiles':
            sql += " GROUP BY p.id, p.cycle_number, p.profile_date, p.latitude, p.longitude, f.wmo_id, f.platform_type"
        else:
            sql += " GROUP BY f.id, f.wmo_id, f.platform_type, f.deployment_date, f.deployment_latitude, f.deployment_longitude, f.status"
        
        # Add ORDER BY with intelligent limit
        sql += f" ORDER BY {date_column} DESC LIMIT {limit}"
        
        logger.info(f"Generated temporal SQL with limit {limit}: {sql}")
        return sql


class EnhancedRAGPipeline(RAGPipeline):
    """Enhanced RAG pipeline with temporal query support."""
    
    def __init__(self):
        super().__init__()
        self.temporal_detector = TemporalQueryDetector()
        self.postgres_executor = PostgreSQLQueryExecutor()
    
    async def initialize(self):
        """Initialize enhanced RAG pipeline."""
        await super().initialize()
        await self.postgres_executor.initialize()
        logger.info("Enhanced RAG pipeline initialized with temporal support")
    
    async def process_query(
        self,
        query: str,
        conversation_id: str = None,
        user_preferences: Dict[str, Any] = None,
        correlation_id: str = None
    ) -> RAGResponse:
        """Process query with temporal query detection and routing."""
        
        start_time = datetime.utcnow()
        correlation_id = correlation_id or f"enhanced_rag_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info(f"Processing query: '{query}' with enhanced RAG pipeline")
            
            # Step 1: Check if this is a temporal query
            is_temporal = self.temporal_detector.is_temporal_query(query)
            
            if is_temporal:
                logger.info("Detected temporal query, routing to PostgreSQL")
                
                # Extract temporal information
                temporal_info = self.temporal_detector.extract_temporal_info(query)
                logger.info(f"Temporal info extracted: {temporal_info}")
                
                # Execute PostgreSQL query
                postgres_results = await self.postgres_executor.execute_temporal_query(query, temporal_info)
                
                # Generate response using PostgreSQL data
                response_text = await self._generate_intelligent_temporal_response(query, postgres_results, temporal_info)
                
                # Calculate confidence based on results found
                confidence_score = 0.9 if postgres_results else 0.1
                
                processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                return RAGResponse(
                    response=response_text,
                    confidence_score=confidence_score,
                    retrieved_contexts=[],
                    sql_query="PostgreSQL temporal query",
                    query_results=postgres_results,
                    generation_metadata={
                        "query_analysis": {
                            "intent": "temporal",
                            "confidence": confidence_score,
                            "temporal_info": temporal_info
                        },
                        "query_type": "temporal",
                        "temporal_info": temporal_info,
                        "postgres_results_count": len(postgres_results),
                        "correlation_id": correlation_id
                    },
                    processing_time_ms=processing_time
                )
            
            else:
                # Route non-temporal queries through LLM as well
                logger.info("Non-temporal query, routing through LLM for intelligent response")
                
                try:
                    # Import Gemini service for intelligent analysis
                    from app.services.real_gemini_service import real_gemini_service
                    
                    # Create prompt for non-temporal queries
                    general_prompt = f"""You are FloatChat, an expert oceanographer and ARGO float data specialist.

USER QUERY: {query}

This is a general oceanographic query that doesn't specify temporal constraints. Please provide a helpful response that:
1. Addresses the user's question as best as possible
2. Explains what type of ARGO float data might be relevant
3. Suggests how they could refine their query for better results
4. Provides relevant oceanographic context
5. Maintains a professional, informative tone

If the query is about specific data analysis, suggest including time periods, geographic regions, or specific measurements (temperature, salinity, pressure) for more targeted results."""

                    # Get intelligent response from Gemini
                    intelligent_response = await real_gemini_service._generate_response(general_prompt)
                    
                    processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    
                    return RAGResponse(
                        response=intelligent_response,
                        confidence_score=0.7,
                        retrieved_contexts=[],
                        generation_metadata={
                            "query_analysis": {
                                "intent": "general",
                                "confidence": 0.7,
                                "language": "en"
                            },
                            "query_type": "general",
                            "correlation_id": correlation_id
                        },
                        processing_time_ms=processing_time
                    )
                    
                except Exception as e:
                    logger.warning(f"LLM processing failed for non-temporal query: {e}")
                    # Emergency fallback if LLM fails
                    processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    
                    return RAGResponse(
                        response=f"I understand you're asking about: {query}. I'm an oceanographic data assistant specializing in ARGO float data. Could you provide more specific details about the time period, geographic region, or type of measurements you're interested in?",
                        confidence_score=0.5,
                        retrieved_contexts=[],
                        generation_metadata={
                            "query_analysis": {
                                "intent": "general",
                                "confidence": 0.5,
                                "language": "en"
                            },
                        "query_type": "general",
                        "correlation_id": correlation_id
                    },
                    processing_time_ms=processing_time
                )
        
        except Exception as e:
            logger.error(f"Enhanced RAG processing failed: {e}")
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return RAGResponse(
                response=f"I apologize, but I encountered an error processing your query: {str(e)}",
                confidence_score=0.0,
                retrieved_contexts=[],
                generation_metadata={
                    "error": str(e),
                    "correlation_id": correlation_id
                },
                processing_time_ms=processing_time
            )
    
    async def _generate_intelligent_temporal_response(self, query: str, results: List[Dict[str, Any]], temporal_info: Dict[str, Any]) -> str:
        """Generate intelligent response using LLM for ALL temporal queries."""
        
        # Always use LLM for consistent, intelligent responses
        try:
            # Import Gemini service for intelligent analysis
            from app.services.real_gemini_service import real_gemini_service
            
            if not results:
                temporal_desc = ""
                if temporal_info['year'] and temporal_info['month']:
                    month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                                  'July', 'August', 'September', 'October', 'November', 'December']
                    temporal_desc = f" for {month_names[temporal_info['month']]} {temporal_info['year']}"
                elif temporal_info['year']:
                    temporal_desc = f" for {temporal_info['year']}"
                
                # Use LLM even for no-data responses
                no_data_prompt = f"""You are FloatChat, an expert oceanographer analyzing ARGO float data.

USER QUERY: {query}

SITUATION: No ARGO float data is available{temporal_desc}. The database might not contain data for this specific time period.

Please provide a helpful response that:
1. Explains that no data is available for the requested period
2. Suggests alternative time periods or approaches
3. Provides context about ARGO float data availability
4. Maintains a professional, helpful tone

Keep the response concise but informative."""

                return await real_gemini_service._generate_response(no_data_prompt)
            
            # Prepare data summary for LLM
            data_summary = self._prepare_data_summary(results, temporal_info)
            
            # Determine query type for appropriate analysis approach
            query_lower = query.lower()
            if any(word in query_lower for word in ['compare', 'comparison', 'versus', 'vs', 'difference', 'trend', 'analyze', 'analysis']):
                analysis_type = "comparative analysis"
            elif any(word in query_lower for word in ['show', 'display', 'list', 'get', 'find']):
                analysis_type = "data presentation"
            elif any(word in query_lower for word in ['available', 'exists', 'have', 'contains']):
                analysis_type = "data availability assessment"
            else:
                analysis_type = "general oceanographic analysis"
            
            # Create enhanced prompt for all temporal queries
            analysis_prompt = f"""You are FloatChat, an expert oceanographer analyzing ARGO float data.

USER QUERY: {query}

QUERY TYPE: {analysis_type}

AVAILABLE DATA SUMMARY:
{data_summary}

Please provide a comprehensive response addressing the user's query. Include:
1. Direct answer to their question
2. Key insights from the data
3. Specific measurements and trends
4. Geographic coverage
5. Any notable patterns or anomalies
6. Scientific context and interpretation

Make your response informative, scientifically accurate, and easy to understand. Use natural language and avoid presenting raw data dumps."""

            # Get intelligent response from Gemini
            intelligent_response = await real_gemini_service._generate_response(analysis_prompt)
            return intelligent_response
            
        except Exception as e:
            logger.warning(f"LLM analysis failed, using fallback response: {e}")
            # Emergency fallback only if LLM completely fails
            if not results:
                return f"I don't have any ARGO float data available for your query. The database might not contain data for this specific time period."
            else:
                return f"I found {len(results)} ARGO profiles matching your query, but I'm unable to provide detailed analysis at the moment. Please try again."
    
    def _prepare_data_summary(self, results: List[Dict[str, Any]], temporal_info: Dict[str, Any]) -> str:
        """Prepare a summary of the data for LLM analysis."""
        if not results:
            return "No data available."
        
        # Extract key statistics
        total_profiles = len(results)
        
        # Get date range
        dates = [r.get('profile_date', '') for r in results if r.get('profile_date')]
        date_range = f"from {min(dates)} to {max(dates)}" if dates else "unknown date range"
        
        # Get geographic coverage
        lats = [float(r.get('latitude', 0)) for r in results if r.get('latitude') is not None]
        lons = [float(r.get('longitude', 0)) for r in results if r.get('longitude') is not None]
        
        geo_summary = ""
        if lats and lons:
            geo_summary = f"Geographic coverage: {min(lats):.2f}°N to {max(lats):.2f}°N, {min(lons):.2f}°E to {max(lons):.2f}°E"
        
        # Get temperature and salinity ranges if available
        temps = [float(r.get('max_temperature', 0)) for r in results if r.get('max_temperature') is not None]
        salinity = [float(r.get('max_salinity', 0)) for r in results if r.get('max_salinity') is not None]
        
        measurement_summary = ""
        if temps:
            measurement_summary += f"Temperature ranges from {min(temps):.2f}°C to {max(temps):.2f}°C. "
        if salinity:
            measurement_summary += f"Salinity ranges from {min(salinity):.2f} to {max(salinity):.2f} PSU."
        
        # Sample profiles for reference
        sample_profiles = []
        for i, result in enumerate(results[:3]):  # First 3 profiles as samples
            float_id = result.get('wmo_id', 'Unknown')
            date = result.get('profile_date', 'Unknown date')
            lat = result.get('latitude', 0)
            lon = result.get('longitude', 0)
            sample_profiles.append(f"• Float {float_id} on {date} at ({lat:.2f}°, {lon:.2f}°)")
        
        summary = f"""ARGO FLOAT DATA SUMMARY:
- Total profiles: {total_profiles}
- Time period: {date_range}
- {geo_summary}
- {measurement_summary}

Sample profiles:
{chr(10).join(sample_profiles)}
{'... and ' + str(total_profiles - 3) + ' more profiles.' if total_profiles > 3 else ''}"""

        return summary

    def _generate_simple_temporal_response(self, query: str, results: List[Dict[str, Any]], temporal_info: Dict[str, Any]) -> str:
        """Generate response for temporal queries using PostgreSQL results."""
        
        if not results:
            temporal_desc = ""
            if temporal_info['year'] and temporal_info['month']:
                month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                              'July', 'August', 'September', 'October', 'November', 'December']
                temporal_desc = f" for {month_names[temporal_info['month']]} {temporal_info['year']}"
            elif temporal_info['year']:
                temporal_desc = f" for {temporal_info['year']}"
            elif temporal_info['is_recent']:
                temporal_desc = " for recent data"
            
            return f"I found no ARGO oceanographic data{temporal_desc} in the database. The data might not be available for this specific time period, or the temporal range might be outside our dataset coverage."
        
        # Generate detailed response based on results
        response_parts = []
        
        # Add summary
        if temporal_info['year'] and temporal_info['month']:
            month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            temporal_desc = f"{month_names[temporal_info['month']]} {temporal_info['year']}"
        elif temporal_info['year']:
            temporal_desc = f"{temporal_info['year']}"
        else:
            temporal_desc = "the requested time period"
        
        response_parts.append(f"I found {len(results)} ARGO profiles for {temporal_desc}.")
        
        # Add details based on data type
        if 'profile_date' in results[0]:
            # Profile data
            dates = [r['profile_date'] for r in results if r['profile_date']]
            if dates:
                date_range = f"from {min(dates)} to {max(dates)}"
                response_parts.append(f"The profiles span {date_range}.")
            
            # Temperature and salinity ranges
            temps = [r for r in results if r.get('min_temp') and r.get('max_temp')]
            if temps:
                min_temp = min(r['min_temp'] for r in temps)
                max_temp = max(r['max_temp'] for r in temps)
                response_parts.append(f"Temperature ranges from {min_temp:.2f}°C to {max_temp:.2f}°C.")
            
            salinities = [r for r in results if r.get('min_salinity') and r.get('max_salinity')]
            if salinities:
                min_sal = min(r['min_salinity'] for r in salinities)
                max_sal = max(r['max_salinity'] for r in salinities)
                response_parts.append(f"Salinity ranges from {min_sal:.2f} to {max_sal:.2f} PSU.")
            
            # Geographic coverage
            lats = [r['latitude'] for r in results if r['latitude']]
            lons = [r['longitude'] for r in results if r['longitude']]
            if lats and lons:
                response_parts.append(f"Geographic coverage: {min(lats):.2f}°N to {max(lats):.2f}°N, {min(lons):.2f}°E to {max(lons):.2f}°E.")
        
        # Add sample data
        response_parts.append("\nSample profiles:")
        for i, result in enumerate(results[:3]):
            if 'profile_date' in result:
                response_parts.append(f"• Float {result.get('wmo_id', 'Unknown')} on {result['profile_date']} at ({result.get('latitude', 0):.2f}°, {result.get('longitude', 0):.2f}°)")
        
        if len(results) > 3:
            response_parts.append(f"... and {len(results) - 3} more profiles.")
        
        return " ".join(response_parts)