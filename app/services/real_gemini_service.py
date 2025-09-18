"""
FloatChat - Real Google Gemini AI Service

Production-ready integration with Google Gemini API for ocean data analysis.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import re

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import httpx

from app.core.config import get_settings
from app.services.real_argo_service import real_argo_service
from app.utils.exceptions import AIServiceError

logger = logging.getLogger(__name__)
settings = get_settings()


class RealGeminiService:
    """Production Gemini AI service for ocean data analysis."""
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model
        self.max_tokens = 2048
        self.temperature = 0.7
        
        # Configure Gemini
        if self.api_key and self.api_key != "demo-key-replace-with-real-key":
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            self.available = True
            logger.info("Real Gemini AI service initialized")
        else:
            self.model = None
            self.available = False
            logger.warning("Gemini API key not configured, using fallback responses")
        
        # Ocean data analysis prompts
        self.system_prompt = """You are FloatChat, an expert AI assistant specialized in ARGO oceanographic data analysis. 

Your expertise includes:
- ARGO float technology and operations
- Ocean temperature, salinity, and pressure analysis  
- Marine biogeochemistry (BGC parameters)
- Oceanographic data interpretation
- Climate and weather patterns affecting oceans
- Marine ecosystem analysis

Guidelines:
- Provide accurate, scientific information about ocean data
- Use real ARGO float data when available
- Explain complex concepts in accessible language
- Include specific data points and measurements when relevant
- Suggest visualization approaches for data
- Be helpful for both researchers and general users
- Always mention data sources and limitations

When users ask about ocean conditions, analyze the provided ARGO data and give insights about:
- Temperature profiles and trends
- Salinity variations and their significance
- Depth-dependent measurements
- Spatial and temporal patterns
- Comparison with climatological norms
- Potential implications for marine life

Respond in a conversational but informative tone."""
    
    async def analyze_ocean_query(self, user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze user query about ocean data using Gemini AI.
        
        Args:
            user_message: User's question about ocean data
            context: Optional context including ARGO data, location, etc.
        
        Returns:
            AI response with analysis and suggestions
        """
        try:
            if not self.available:
                return self._get_fallback_response(user_message, context)
            
            # Extract location and parameters from query
            query_analysis = await self._analyze_query_intent(user_message)
            
            # Fetch relevant ARGO data if location is specified
            argo_data = None
            if query_analysis.get('location'):
                try:
                    lat, lon = query_analysis['location']
                    argo_data = await real_argo_service.get_ocean_conditions(lat, lon, radius_km=200)
                except Exception as e:
                    logger.warning(f"Failed to fetch ARGO data for location: {e}")
            
            # Build enhanced prompt with context
            prompt = self._build_analysis_prompt(user_message, query_analysis, argo_data, context)
            
            # Generate response using Gemini
            response = await self._generate_response(prompt)
            
            # Parse and structure the response
            result = {
                'message': response,
                'query_type': query_analysis.get('type', 'general'),
                'location': query_analysis.get('location'),
                'parameters': query_analysis.get('parameters', []),
                'data_sources': [],
                'timestamp': datetime.now().isoformat(),
                'confidence': 0.9
            }
            
            if argo_data:
                result['data_sources'].append('ARGO Global Data Assembly Centre')
                result['argo_data'] = argo_data
                
                # Add visualization suggestion
                if query_analysis.get('parameters'):
                    result['visualization'] = self._suggest_visualization(
                        query_analysis['parameters'], argo_data
                    )
            
            logger.info("Generated AI response for ocean query", 
                       query_type=result['query_type'],
                       has_argo_data=argo_data is not None)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze ocean query: {e}")
            return self._get_error_response(user_message, str(e))
    
    async def _analyze_query_intent(self, message: str) -> Dict[str, Any]:
        """Analyze user query to extract intent, location, and parameters."""
        
        # Extract locations (basic patterns)
        location_patterns = [
            r'(?:near|around|in|at)\s+([A-Za-z\s]+(?:Sea|Ocean|Bay|Gulf|Coast))',
            r'(?:latitude|lat)\s*:?\s*([+-]?\d+\.?\d*)[°\s]*(?:longitude|lon|lng)\s*:?\s*([+-]?\d+\.?\d*)',
            r'([+-]?\d+\.?\d*)[°\s]*[NS]\s*[,\s]*([+-]?\d+\.?\d*)[°\s]*[EW]'
        ]
        
        location = None
        for pattern in location_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:  # Lat/lon coordinates
                    try:
                        lat = float(match.group(1))
                        lon = float(match.group(2))
                        location = (lat, lon)
                        break
                    except ValueError:
                        continue
                else:  # Named location
                    location_name = match.group(1).strip()
                    # Convert named locations to coordinates (simplified)
                    location = self._get_location_coordinates(location_name)
                    break
        
        # Extract parameters
        parameters = []
        param_patterns = {
            'temperature': r'(?:temperature|temp|thermal)',
            'salinity': r'(?:salinity|salt|saline)',
            'pressure': r'(?:pressure|depth)',
            'oxygen': r'(?:oxygen|O2|dissolved oxygen)',
            'chlorophyll': r'(?:chlorophyll|chl|phytoplankton)',
            'ph': r'(?:pH|acidity|alkalinity)'
        }
        
        for param, pattern in param_patterns.items():
            if re.search(pattern, message, re.IGNORECASE):
                parameters.append(param)
        
        # Determine query type
        query_type = 'general'
        if location:
            query_type = 'location_specific'
        if parameters:
            query_type = 'parameter_analysis'
        if 'trend' in message.lower() or 'change' in message.lower():
            query_type = 'trend_analysis'
        if 'compare' in message.lower() or 'comparison' in message.lower():
            query_type = 'comparison'
        
        return {
            'type': query_type,
            'location': location,
            'parameters': parameters,
            'original_message': message
        }
    
    def _get_location_coordinates(self, location_name: str) -> Optional[Tuple[float, float]]:
        """Convert named location to coordinates (simplified mapping)."""
        locations = {
            'arabian sea': (15.0, 65.0),
            'bay of bengal': (15.0, 87.0),
            'indian ocean': (-20.0, 75.0),
            'mumbai': (19.1, 72.9),
            'chennai': (13.1, 80.3),
            'kochi': (9.9, 76.3),
            'goa': (15.5, 73.8),
            'andaman sea': (10.0, 95.0)
        }
        
        location_lower = location_name.lower().strip()
        return locations.get(location_lower)
    
    def _build_analysis_prompt(self, user_message: str, query_analysis: Dict[str, Any], 
                             argo_data: Optional[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """Build comprehensive prompt for Gemini analysis."""
        
        prompt_parts = [self.system_prompt, "\n\nUser Query:", user_message]
        
        if query_analysis.get('location'):
            lat, lon = query_analysis['location']
            prompt_parts.extend([
                f"\nQuery Location: {lat:.3f}°, {lon:.3f}°"
            ])
        
        if query_analysis.get('parameters'):
            prompt_parts.extend([
                f"\nRequested Parameters: {', '.join(query_analysis['parameters'])}"
            ])
        
        if argo_data:
            prompt_parts.extend([
                "\nReal ARGO Data Available:",
                f"- {argo_data['floats_found']} active floats in region",
                f"- Search radius: {argo_data['search_radius_km']} km"
            ])
            
            if argo_data.get('summary'):
                summary = argo_data['summary']
                if 'temperature' in summary:
                    temp = summary['temperature']
                    prompt_parts.append(
                        f"- Temperature: {temp['mean']:.1f}°C ±{temp['std']:.1f}°C "
                        f"(range: {temp['min']:.1f}-{temp['max']:.1f}°C, n={temp['count']})"
                    )
                
                if 'salinity' in summary:
                    sal = summary['salinity']
                    prompt_parts.append(
                        f"- Salinity: {sal['mean']:.2f} ±{sal['std']:.2f} PSU "
                        f"(range: {sal['min']:.2f}-{sal['max']:.2f} PSU, n={sal['count']})"
                    )
            
            # Add recent measurements
            recent_measurements = argo_data.get('measurements', [])[:3]
            if recent_measurements:
                prompt_parts.append("\nRecent Measurements:")
                for i, measurement in enumerate(recent_measurements, 1):
                    prompt_parts.append(
                        f"{i}. WMO {measurement['wmo_id']} ({measurement['date'][:10]}): "
                        f"T={measurement.get('surface_temp', 'N/A')}°C, "
                        f"S={measurement.get('surface_salinity', 'N/A')} PSU"
                    )
        
        if context:
            if context.get('conversation_history'):
                prompt_parts.extend([
                    "\nConversation Context:",
                    str(context['conversation_history'][-3:])  # Last 3 messages
                ])
        
        prompt_parts.extend([
            "\nProvide a comprehensive analysis addressing the user's question.",
            "Include specific data interpretations, scientific insights, and practical implications.",
            "If suggesting visualizations, be specific about chart types and data presentation.",
            "Keep the response informative but accessible to both experts and general users."
        ])
        
        return "\n".join(prompt_parts)
    
    async def _generate_response(self, prompt: str) -> str:
        """Generate response using Gemini API."""
        try:
            # Configure safety settings
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # Generate content
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                safety_settings=safety_settings,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                )
            )
            
            if response.candidates:
                return response.candidates[0].content.parts[0].text
            else:
                raise AIServiceError("No response generated by Gemini")
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise AIServiceError(f"Failed to generate AI response: {e}")
    
    def _suggest_visualization(self, parameters: List[str], argo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest appropriate visualization based on parameters and data."""
        
        viz_suggestions = {
            'temperature': {
                'chart_type': 'line_chart',
                'title': 'Temperature Profile vs Depth',
                'x_axis': 'Temperature (°C)',
                'y_axis': 'Depth (m)',
                'description': 'Shows how temperature changes with ocean depth'
            },
            'salinity': {
                'chart_type': 'line_chart', 
                'title': 'Salinity Profile vs Depth',
                'x_axis': 'Salinity (PSU)',
                'y_axis': 'Depth (m)',
                'description': 'Shows salinity variation with depth'
            },
            'temperature_salinity': {
                'chart_type': 'scatter_plot',
                'title': 'Temperature-Salinity Diagram',
                'x_axis': 'Salinity (PSU)',
                'y_axis': 'Temperature (°C)',
                'description': 'T-S diagram showing water mass characteristics'
            }
        }
        
        # Determine best visualization
        if 'temperature' in parameters and 'salinity' in parameters:
            return viz_suggestions['temperature_salinity']
        elif 'temperature' in parameters:
            return viz_suggestions['temperature']
        elif 'salinity' in parameters:
            return viz_suggestions['salinity']
        else:
            return {
                'chart_type': 'map',
                'title': 'ARGO Float Locations',
                'description': 'Geographic distribution of measurement locations'
            }
    
    def _get_fallback_response(self, user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate fallback response when Gemini API is unavailable."""
        
        responses = {
            'temperature': "Based on ARGO float data, ocean temperatures in your region typically range from 26-29°C at the surface, decreasing with depth. The thermocline usually occurs around 100-200m depth where temperature drops rapidly.",
            'salinity': "Ocean salinity in most regions ranges from 34-36 PSU (Practical Salinity Units). Surface salinity is influenced by evaporation, precipitation, and freshwater input from rivers.",
            'general': "I'd be happy to help analyze ocean data! ARGO floats provide valuable measurements of temperature, salinity, and pressure throughout the water column. What specific aspect of ocean conditions would you like to explore?"
        }
        
        # Simple keyword matching for fallback
        message_lower = user_message.lower()
        if 'temperature' in message_lower:
            response_key = 'temperature'
        elif 'salinity' in message_lower:
            response_key = 'salinity'  
        else:
            response_key = 'general'
        
        return {
            'message': responses[response_key],
            'query_type': 'fallback',
            'data_sources': ['Built-in oceanographic knowledge'],
            'timestamp': datetime.now().isoformat(),
            'confidence': 0.6,
            'note': 'This is a fallback response. For detailed analysis, please configure the Gemini API key.'
        }
    
    def _get_error_response(self, user_message: str, error: str) -> Dict[str, Any]:
        """Generate error response."""
        return {
            'message': f"I encountered an error while analyzing your ocean data query: {error}. Please try rephrasing your question or contact support if the issue persists.",
            'query_type': 'error',
            'error': error,
            'timestamp': datetime.now().isoformat(),
            'confidence': 0.0
        }


# Global service instance
real_gemini_service = RealGeminiService()
