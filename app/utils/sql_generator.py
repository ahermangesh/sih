"""
FloatChat - SQL Generation Utilities

Natural language to SQL translation with security validation, query optimization,
and performance monitoring for ARGO oceanographic data queries.
"""

import re
import json
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

import sqlparse
from sqlparse import sql, tokens
import structlog

from app.services.nlu_service import QueryAnalysis, QueryIntent, SpatialScope, TemporalScope, ParameterScope
from app.utils.exceptions import ValidationError, DatabaseError

logger = structlog.get_logger(__name__)


class QueryType(Enum):
    """Types of SQL queries that can be generated."""
    SELECT = "SELECT"
    COUNT = "COUNT"
    AGGREGATE = "AGGREGATE"
    SPATIAL = "SPATIAL"
    TEMPORAL = "TEMPORAL"


@dataclass
class QueryTemplate:
    """Template for SQL query generation."""
    name: str
    intent: QueryIntent
    query_type: QueryType
    base_query: str
    joins: List[str] = field(default_factory=list)
    where_conditions: List[str] = field(default_factory=list)
    spatial_conditions: List[str] = field(default_factory=list)
    temporal_conditions: List[str] = field(default_factory=list)
    aggregations: List[str] = field(default_factory=list)
    order_by: List[str] = field(default_factory=list)
    limit_clause: Optional[str] = None
    description: str = ""


@dataclass
class GeneratedQuery:
    """Container for generated SQL query with metadata."""
    sql: str
    parameters: Dict[str, Any]
    query_type: QueryType
    estimated_rows: Optional[int] = None
    execution_plan: Optional[str] = None
    security_validated: bool = False
    performance_warnings: List[str] = field(default_factory=list)
    explanation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class QueryTemplateManager:
    """Manages SQL query templates for different intents."""
    
    def __init__(self):
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[QueryIntent, List[QueryTemplate]]:
        """Initialize query templates for different intents."""
        return {
            QueryIntent.GET_FLOAT_INFO: [
                QueryTemplate(
                    name="float_basic_info",
                    intent=QueryIntent.GET_FLOAT_INFO,
                    query_type=QueryType.SELECT,
                    base_query="""
                        SELECT 
                            f.wmo_id,
                            f.platform_number,
                            f.float_type,
                            f.data_center,
                            f.project_name,
                            f.pi_name,
                            f.deployment_date,
                            f.deployment_latitude,
                            f.deployment_longitude,
                            f.status,
                            f.last_profile_date,
                            f.total_profiles,
                            f.quality_flag
                        FROM argo_floats f
                    """,
                    description="Get basic information about a specific ARGO float"
                ),
                QueryTemplate(
                    name="float_with_recent_profiles",
                    intent=QueryIntent.GET_FLOAT_INFO,
                    query_type=QueryType.SELECT,
                    base_query="""
                        SELECT 
                            f.*,
                            COUNT(p.id) as profile_count,
                            MAX(p.profile_date) as latest_profile_date,
                            MIN(p.profile_date) as earliest_profile_date
                        FROM argo_floats f
                        LEFT JOIN argo_profiles p ON f.id = p.float_id
                    """,
                    joins=["LEFT JOIN argo_profiles p ON f.id = p.float_id"],
                    aggregations=["COUNT(p.id) as profile_count", "MAX(p.profile_date) as latest_profile_date"],
                    order_by=["f.wmo_id"],
                    description="Get float information with profile statistics"
                )
            ],
            
            QueryIntent.SEARCH_FLOATS: [
                QueryTemplate(
                    name="floats_by_region",
                    intent=QueryIntent.SEARCH_FLOATS,
                    query_type=QueryType.SPATIAL,
                    base_query="""
                        SELECT 
                            f.wmo_id,
                            f.platform_number,
                            f.deployment_latitude,
                            f.deployment_longitude,
                            f.status,
                            f.total_profiles,
                            ST_Distance(
                                ST_SetSRID(ST_MakePoint(f.deployment_longitude, f.deployment_latitude), 4326),
                                ST_SetSRID(ST_MakePoint(%(center_lon)s, %(center_lat)s), 4326)
                            ) as distance_km
                        FROM argo_floats f
                    """,
                    spatial_conditions=[
                        "f.deployment_latitude IS NOT NULL",
                        "f.deployment_longitude IS NOT NULL"
                    ],
                    order_by=["distance_km"],
                    limit_clause="LIMIT %(limit)s",
                    description="Find floats within a geographic region"
                ),
                QueryTemplate(
                    name="floats_in_bbox",
                    intent=QueryIntent.SEARCH_FLOATS,
                    query_type=QueryType.SPATIAL,
                    base_query="""
                        SELECT 
                            f.wmo_id,
                            f.platform_number,
                            f.deployment_latitude,
                            f.deployment_longitude,
                            f.deployment_date,
                            f.status,
                            f.total_profiles
                        FROM argo_floats f
                    """,
                    spatial_conditions=[
                        "f.deployment_latitude BETWEEN %(south)s AND %(north)s",
                        "f.deployment_longitude BETWEEN %(west)s AND %(east)s"
                    ],
                    order_by=["f.deployment_date DESC"],
                    limit_clause="LIMIT %(limit)s",
                    description="Find floats within a bounding box"
                )
            ],
            
            QueryIntent.GET_PROFILES: [
                QueryTemplate(
                    name="profiles_by_float",
                    intent=QueryIntent.GET_PROFILES,
                    query_type=QueryType.SELECT,
                    base_query="""
                        SELECT 
                            p.cycle_number,
                            p.profile_date,
                            p.latitude,
                            p.longitude,
                            p.max_pressure,
                            p.min_temperature,
                            p.max_temperature,
                            p.min_salinity,
                            p.max_salinity,
                            p.has_temperature,
                            p.has_salinity,
                            p.has_oxygen,
                            p.quality_flag
                        FROM argo_profiles p
                        JOIN argo_floats f ON p.float_id = f.id
                    """,
                    joins=["JOIN argo_floats f ON p.float_id = f.id"],
                    order_by=["p.profile_date DESC"],
                    limit_clause="LIMIT %(limit)s",
                    description="Get profiles for a specific float"
                ),
                QueryTemplate(
                    name="profiles_by_region_time",
                    intent=QueryIntent.GET_PROFILES,
                    query_type=QueryType.SPATIAL,
                    base_query="""
                        SELECT 
                            f.wmo_id,
                            p.cycle_number,
                            p.profile_date,
                            p.latitude,
                            p.longitude,
                            p.max_pressure,
                            p.min_temperature,
                            p.max_temperature,
                            p.min_salinity,
                            p.max_salinity
                        FROM argo_profiles p
                        JOIN argo_floats f ON p.float_id = f.id
                    """,
                    joins=["JOIN argo_floats f ON p.float_id = f.id"],
                    order_by=["p.profile_date DESC", "f.wmo_id"],
                    limit_clause="LIMIT %(limit)s",
                    description="Get profiles within region and time period"
                )
            ],
            
            QueryIntent.ANALYZE_TEMPERATURE: [
                QueryTemplate(
                    name="temperature_statistics",
                    intent=QueryIntent.ANALYZE_TEMPERATURE,
                    query_type=QueryType.AGGREGATE,
                    base_query="""
                        SELECT 
                            COUNT(*) as profile_count,
                            AVG(p.min_temperature) as avg_min_temp,
                            AVG(p.max_temperature) as avg_max_temp,
                            MIN(p.min_temperature) as overall_min_temp,
                            MAX(p.max_temperature) as overall_max_temp,
                            STDDEV(p.min_temperature) as min_temp_stddev,
                            STDDEV(p.max_temperature) as max_temp_stddev
                        FROM argo_profiles p
                        JOIN argo_floats f ON p.float_id = f.id
                    """,
                    joins=["JOIN argo_floats f ON p.float_id = f.id"],
                    where_conditions=["p.has_temperature = true"],
                    description="Calculate temperature statistics for profiles"
                ),
                QueryTemplate(
                    name="temperature_depth_analysis",
                    intent=QueryIntent.ANALYZE_TEMPERATURE,
                    query_type=QueryType.SELECT,
                    base_query="""
                        SELECT 
                            f.wmo_id,
                            p.cycle_number,
                            p.profile_date,
                            m.pressure,
                            m.depth,
                            m.temperature,
                            m.temperature_qf
                        FROM argo_measurements m
                        JOIN argo_profiles p ON m.profile_id = p.id
                        JOIN argo_floats f ON p.float_id = f.id
                    """,
                    joins=[
                        "JOIN argo_profiles p ON m.profile_id = p.id",
                        "JOIN argo_floats f ON p.float_id = f.id"
                    ],
                    where_conditions=[
                        "m.temperature IS NOT NULL",
                        "m.temperature_qf IN ('1', '2')"  # Good quality data
                    ],
                    order_by=["p.profile_date", "m.pressure"],
                    limit_clause="LIMIT %(limit)s",
                    description="Get temperature measurements with depth information"
                )
            ],
            
            QueryIntent.ANALYZE_SALINITY: [
                QueryTemplate(
                    name="salinity_statistics",
                    intent=QueryIntent.ANALYZE_SALINITY,
                    query_type=QueryType.AGGREGATE,
                    base_query="""
                        SELECT 
                            COUNT(*) as profile_count,
                            AVG(p.min_salinity) as avg_min_salinity,
                            AVG(p.max_salinity) as avg_max_salinity,
                            MIN(p.min_salinity) as overall_min_salinity,
                            MAX(p.max_salinity) as overall_max_salinity,
                            STDDEV(p.min_salinity) as min_salinity_stddev,
                            STDDEV(p.max_salinity) as max_salinity_stddev
                        FROM argo_profiles p
                        JOIN argo_floats f ON p.float_id = f.id
                    """,
                    joins=["JOIN argo_floats f ON p.float_id = f.id"],
                    where_conditions=["p.has_salinity = true"],
                    description="Calculate salinity statistics for profiles"
                )
            ]
        }
    
    def get_templates(self, intent: QueryIntent) -> List[QueryTemplate]:
        """Get templates for a specific intent."""
        return self.templates.get(intent, [])
    
    def get_best_template(
        self, 
        intent: QueryIntent, 
        analysis: QueryAnalysis
    ) -> Optional[QueryTemplate]:
        """Select the best template based on query analysis."""
        templates = self.get_templates(intent)
        if not templates:
            return None
        
        # Simple selection logic - can be enhanced with ML
        for template in templates:
            # Check if template matches spatial requirements
            if (analysis.spatial_scope.coordinates and 
                template.query_type in [QueryType.SPATIAL]):
                return template
            
            # Check if template matches temporal requirements
            if (analysis.temporal_scope.start_date and 
                template.query_type in [QueryType.TEMPORAL]):
                return template
            
            # Check for aggregation requirements
            if ("statistics" in template.name and 
                any(word in analysis.original_query.lower() 
                    for word in ["average", "mean", "statistics", "summary"])):
                return template
        
        # Return first template as default
        return templates[0]


class ParameterBinder:
    """Bind parameters to SQL queries with type safety."""
    
    def __init__(self):
        self.parameter_types = {
            'wmo_id': str,
            'platform_number': str,
            'start_date': date,
            'end_date': date,
            'north': float,
            'south': float,
            'east': float,
            'west': float,
            'center_lat': float,
            'center_lon': float,
            'min_pressure': float,
            'max_pressure': float,
            'limit': int,
            'offset': int
        }
    
    def bind_parameters(
        self, 
        template: QueryTemplate,
        analysis: QueryAnalysis,
        additional_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Bind parameters from query analysis to template."""
        parameters = {}
        
        # Extract parameters from entities
        for entity in analysis.entities:
            if entity.label == "FLOAT_ID":
                # Extract WMO ID from float ID entity
                wmo_match = re.search(r'\d{7,10}', entity.text)
                if wmo_match:
                    parameters['wmo_id'] = wmo_match.group()
        
        # Spatial parameters
        if analysis.spatial_scope.coordinates:
            west, south, east, north = analysis.spatial_scope.coordinates
            parameters.update({
                'west': west,
                'south': south,
                'east': east,
                'north': north,
                'center_lat': (south + north) / 2,
                'center_lon': (west + east) / 2
            })
        
        # Temporal parameters
        if analysis.temporal_scope.start_date:
            parameters['start_date'] = analysis.temporal_scope.start_date
        if analysis.temporal_scope.end_date:
            parameters['end_date'] = analysis.temporal_scope.end_date
        
        # Default parameters
        parameters.setdefault('limit', 100)
        parameters.setdefault('offset', 0)
        
        # Add additional parameters
        if additional_params:
            parameters.update(additional_params)
        
        # Validate parameter types
        validated_parameters = {}
        for key, value in parameters.items():
            if key in self.parameter_types:
                expected_type = self.parameter_types[key]
                try:
                    if expected_type == date and isinstance(value, str):
                        validated_parameters[key] = datetime.strptime(value, "%Y-%m-%d").date()
                    else:
                        validated_parameters[key] = expected_type(value)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Parameter type conversion failed: {key}={value}", error=str(e))
                    continue
            else:
                validated_parameters[key] = value
        
        return validated_parameters


class QueryValidator:
    """Validate SQL queries for security and syntax."""
    
    def __init__(self):
        self.dangerous_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE',
            'TRUNCATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE',
            'UNION', 'SCRIPT', 'DECLARE', 'CURSOR'
        ]
        
        self.allowed_functions = [
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'STDDEV',
            'ST_Distance', 'ST_SetSRID', 'ST_MakePoint',
            'EXTRACT', 'DATE_PART', 'NOW', 'CURRENT_DATE'
        ]
    
    def validate_query(self, sql: str) -> Tuple[bool, List[str]]:
        """
        Validate SQL query for security and syntax.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        try:
            # Parse SQL
            parsed = sqlparse.parse(sql)
            if not parsed:
                errors.append("Failed to parse SQL query")
                return False, errors
            
            # Check for dangerous keywords
            sql_upper = sql.upper()
            for keyword in self.dangerous_keywords:
                if keyword in sql_upper:
                    errors.append(f"Dangerous keyword detected: {keyword}")
            
            # Check for SQL injection patterns
            injection_patterns = [
                r"';.*--",  # Comment injection
                r"UNION\s+SELECT",  # Union injection
                r"OR\s+1\s*=\s*1",  # Boolean injection
                r"AND\s+1\s*=\s*0",  # Boolean injection
            ]
            
            for pattern in injection_patterns:
                if re.search(pattern, sql_upper):
                    errors.append(f"Potential SQL injection pattern detected")
            
            # Validate that query is read-only
            statement = parsed[0]
            if statement.get_type() != 'SELECT':
                errors.append("Only SELECT queries are allowed")
            
            # Check for excessive complexity
            if sql.count('JOIN') > 5:
                errors.append("Query has too many JOINs (max 5)")
            
            if sql.count('SELECT') > 3:
                errors.append("Query has too many subqueries (max 3)")
            
        except Exception as e:
            errors.append(f"Query validation error: {str(e)}")
        
        return len(errors) == 0, errors
    
    def sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters to prevent injection."""
        sanitized = {}
        
        for key, value in parameters.items():
            if isinstance(value, str):
                # Remove potentially dangerous characters
                sanitized_value = re.sub(r"[';\"\\]", "", value)
                sanitized[key] = sanitized_value
            else:
                sanitized[key] = value
        
        return sanitized


class QueryOptimizer:
    """Optimize SQL queries for performance."""
    
    def __init__(self):
        self.optimization_rules = [
            self._add_spatial_index_hints,
            self._add_temporal_index_hints,
            self._optimize_joins,
            self._add_limit_clauses,
        ]
    
    def optimize_query(self, sql: str, parameters: Dict[str, Any]) -> Tuple[str, List[str]]:
        """
        Optimize SQL query for performance.
        
        Returns:
            Tuple of (optimized_sql, optimization_notes)
        """
        optimized_sql = sql
        optimization_notes = []
        
        for rule in self.optimization_rules:
            try:
                optimized_sql, notes = rule(optimized_sql, parameters)
                optimization_notes.extend(notes)
            except Exception as e:
                logger.warning(f"Optimization rule failed: {str(e)}")
        
        return optimized_sql, optimization_notes
    
    def _add_spatial_index_hints(self, sql: str, parameters: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Add spatial index hints for geographic queries."""
        notes = []
        
        # Check if query uses spatial conditions
        if any(param in parameters for param in ['north', 'south', 'east', 'west']):
            # Ensure spatial index usage
            if 'deployment_latitude BETWEEN' in sql and 'deployment_longitude BETWEEN' in sql:
                notes.append("Using spatial indexes for geographic filtering")
            
            # Suggest using PostGIS functions for better performance
            if 'ST_Distance' not in sql and 'distance' in sql.lower():
                notes.append("Consider using ST_Distance for accurate distance calculations")
        
        return sql, notes
    
    def _add_temporal_index_hints(self, sql: str, parameters: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Add temporal index hints for date range queries."""
        notes = []
        
        if any(param in parameters for param in ['start_date', 'end_date']):
            if 'profile_date' in sql:
                notes.append("Using temporal indexes for date filtering")
        
        return sql, notes
    
    def _optimize_joins(self, sql: str, parameters: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Optimize JOIN operations."""
        notes = []
        
        # Count JOINs
        join_count = sql.upper().count('JOIN')
        if join_count > 2:
            notes.append(f"Query has {join_count} JOINs - consider query optimization")
        
        return sql, notes
    
    def _add_limit_clauses(self, sql: str, parameters: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Ensure queries have reasonable LIMIT clauses."""
        notes = []
        
        if 'LIMIT' not in sql.upper():
            # Add default limit if none exists
            limit_value = parameters.get('limit', 1000)
            sql = f"{sql.rstrip(';')} LIMIT {limit_value}"
            notes.append(f"Added LIMIT {limit_value} for performance")
        
        return sql, notes


class QueryExplainer:
    """Generate human-readable explanations of SQL queries."""
    
    def __init__(self):
        self.explanation_templates = {
            'float_info': "Retrieving information about ARGO float {wmo_id}",
            'spatial_search': "Searching for floats in the region between {south}°N-{north}°N and {west}°E-{east}°E",
            'temporal_filter': "Filtering data from {start_date} to {end_date}",
            'temperature_analysis': "Analyzing temperature data from oceanographic profiles",
            'aggregate_query': "Calculating statistical summaries of oceanographic measurements"
        }
    
    def explain_query(
        self, 
        template: QueryTemplate,
        parameters: Dict[str, Any],
        analysis: QueryAnalysis
    ) -> str:
        """Generate human-readable explanation of the query."""
        
        explanation_parts = []
        
        # Base explanation from template
        if template.description:
            explanation_parts.append(template.description)
        
        # Add spatial context
        if analysis.spatial_scope.coordinates:
            west, south, east, north = analysis.spatial_scope.coordinates
            explanation_parts.append(
                f"within the geographic region {south:.2f}°-{north:.2f}°N, {west:.2f}°-{east:.2f}°E"
            )
        
        if analysis.spatial_scope.locations:
            locations = ", ".join(analysis.spatial_scope.locations)
            explanation_parts.append(f"in the area of {locations}")
        
        # Add temporal context
        if analysis.temporal_scope.start_date and analysis.temporal_scope.end_date:
            explanation_parts.append(
                f"from {analysis.temporal_scope.start_date} to {analysis.temporal_scope.end_date}"
            )
        elif analysis.temporal_scope.relative_time:
            explanation_parts.append(f"for the {analysis.temporal_scope.relative_time}")
        
        # Add parameter context
        if analysis.parameter_scope.measurements:
            measurements = ", ".join(analysis.parameter_scope.measurements)
            explanation_parts.append(f"focusing on {measurements} measurements")
        
        # Combine parts
        if explanation_parts:
            return ". ".join(explanation_parts) + "."
        else:
            return "Executing oceanographic data query."


class NL2SQLTranslator:
    """Main class for natural language to SQL translation."""
    
    def __init__(self):
        self.template_manager = QueryTemplateManager()
        self.parameter_binder = ParameterBinder()
        self.query_validator = QueryValidator()
        self.query_optimizer = QueryOptimizer()
        self.query_explainer = QueryExplainer()
    
    async def translate_query(
        self,
        analysis: QueryAnalysis,
        additional_params: Dict[str, Any] = None,
        optimize: bool = True,
        correlation_id: str = None
    ) -> GeneratedQuery:
        """
        Translate natural language query analysis to SQL.
        
        Args:
            analysis: Query analysis from NLU service
            additional_params: Additional query parameters
            optimize: Whether to optimize the generated query
            correlation_id: Request correlation ID
            
        Returns:
            Generated SQL query with metadata
        """
        try:
            logger.info(
                "Translating query to SQL",
                intent=analysis.intent.value,
                confidence=analysis.confidence,
                correlation_id=correlation_id
            )
            
            # Get appropriate template
            template = self.template_manager.get_best_template(analysis.intent, analysis)
            if not template:
                raise ValidationError(
                    f"No SQL template available for intent: {analysis.intent.value}"
                )
            
            # Bind parameters
            parameters = self.parameter_binder.bind_parameters(
                template, analysis, additional_params
            )
            
            # Build base query
            sql_parts = [template.base_query]
            
            # Add WHERE conditions
            where_conditions = []
            
            # Add template conditions
            where_conditions.extend(template.where_conditions)
            where_conditions.extend(template.spatial_conditions)
            where_conditions.extend(template.temporal_conditions)
            
            # Add dynamic conditions based on analysis
            if analysis.spatial_scope.coordinates:
                if 'north' in parameters and 'south' in parameters:
                    where_conditions.extend([
                        "f.deployment_latitude BETWEEN %(south)s AND %(north)s",
                        "f.deployment_longitude BETWEEN %(west)s AND %(east)s"
                    ])
            
            if analysis.temporal_scope.start_date:
                where_conditions.append("p.profile_date >= %(start_date)s")
            if analysis.temporal_scope.end_date:
                where_conditions.append("p.profile_date <= %(end_date)s")
            
            # Add entity-based conditions
            for entity in analysis.entities:
                if entity.label == "FLOAT_ID" and 'wmo_id' in parameters:
                    where_conditions.append("f.wmo_id = %(wmo_id)s")
            
            # Build complete query
            if where_conditions:
                where_clause = " WHERE " + " AND ".join(where_conditions)
                sql_parts.append(where_clause)
            
            # Add GROUP BY for aggregate queries
            if template.aggregations:
                group_by_fields = []
                for field in ['f.wmo_id', 'p.cycle_number', 'p.profile_date']:
                    if field in template.base_query and field not in template.aggregations:
                        group_by_fields.append(field)
                
                if group_by_fields:
                    sql_parts.append(f" GROUP BY {', '.join(group_by_fields)}")
            
            # Add ORDER BY
            if template.order_by:
                sql_parts.append(f" ORDER BY {', '.join(template.order_by)}")
            
            # Add LIMIT
            if template.limit_clause:
                sql_parts.append(f" {template.limit_clause}")
            
            # Combine SQL parts
            sql = " ".join(sql_parts)
            
            # Sanitize parameters
            parameters = self.query_validator.sanitize_parameters(parameters)
            
            # Validate query
            is_valid, validation_errors = self.query_validator.validate_query(sql)
            if not is_valid:
                raise ValidationError(f"Query validation failed: {'; '.join(validation_errors)}")
            
            # Optimize query
            optimization_notes = []
            if optimize:
                sql, optimization_notes = self.query_optimizer.optimize_query(sql, parameters)
            
            # Generate explanation
            explanation = self.query_explainer.explain_query(template, parameters, analysis)
            
            # Create result
            generated_query = GeneratedQuery(
                sql=sql,
                parameters=parameters,
                query_type=template.query_type,
                security_validated=True,
                explanation=explanation,
                metadata={
                    "template_name": template.name,
                    "intent": analysis.intent.value,
                    "optimization_notes": optimization_notes,
                    "generation_timestamp": datetime.utcnow().isoformat(),
                    "correlation_id": correlation_id
                }
            )
            
            logger.info(
                "SQL query generated successfully",
                template_name=template.name,
                parameter_count=len(parameters),
                optimization_notes_count=len(optimization_notes),
                correlation_id=correlation_id
            )
            
            return generated_query
            
        except Exception as e:
            logger.error(
                "SQL generation failed",
                error=str(e),
                intent=analysis.intent.value if analysis else "unknown",
                correlation_id=correlation_id,
                exc_info=True
            )
            raise ValidationError(f"Failed to generate SQL query: {str(e)}")
    
    def estimate_query_performance(self, generated_query: GeneratedQuery) -> Dict[str, Any]:
        """Estimate query performance characteristics."""
        performance_estimate = {
            "complexity": "medium",
            "estimated_execution_time": "< 1 second",
            "estimated_rows": "< 1000",
            "performance_warnings": generated_query.performance_warnings,
            "optimization_suggestions": []
        }
        
        # Analyze query complexity
        sql = generated_query.sql.upper()
        join_count = sql.count('JOIN')
        subquery_count = sql.count('SELECT') - 1
        
        if join_count > 3 or subquery_count > 2:
            performance_estimate["complexity"] = "high"
            performance_estimate["estimated_execution_time"] = "1-5 seconds"
            performance_estimate["optimization_suggestions"].append(
                "Consider adding more specific filters to reduce result set"
            )
        
        # Check for spatial queries
        if any(func in sql for func in ['ST_DISTANCE', 'ST_WITHIN']):
            performance_estimate["optimization_suggestions"].append(
                "Spatial operations may benefit from additional spatial indexes"
            )
        
        return performance_estimate
