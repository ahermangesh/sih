"""
FloatChat - Natural Language Understanding Service

Comprehensive NLU engine for oceanographic queries with intent classification,
entity extraction, parameter parsing, and multilingual support.
"""

import re
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

import spacy
from spacy.matcher import Matcher
from spacy.util import filter_spans
import structlog
from langdetect import detect, detect_langs

# Optional translation backends
try:  # Preferred lightweight backend without httpx pinning issues
    from deep_translator import GoogleTranslator as DeepTranslator  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    DeepTranslator = None  # type: ignore

try:  # Fallback if available
    from googletrans import Translator as GoogleTransTranslator  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    GoogleTransTranslator = None  # type: ignore

from app.core.config import get_settings
from app.utils.exceptions import ValidationError, AIServiceError

logger = structlog.get_logger(__name__)


class QueryIntent(Enum):
    """Enumeration of supported query intents."""
    
    # Data retrieval intents
    GET_FLOAT_INFO = "get_float_info"
    GET_PROFILES = "get_profiles"
    GET_MEASUREMENTS = "get_measurements"
    SEARCH_FLOATS = "search_floats"
    
    # Analysis intents
    ANALYZE_TEMPERATURE = "analyze_temperature"
    ANALYZE_SALINITY = "analyze_salinity"
    ANALYZE_OXYGEN = "analyze_oxygen"
    COMPARE_PROFILES = "compare_profiles"
    TREND_ANALYSIS = "trend_analysis"
    
    # Visualization intents
    SHOW_MAP = "show_map"
    PLOT_PROFILE = "plot_profile"
    CREATE_CHART = "create_chart"
    SHOW_TRAJECTORY = "show_trajectory"
    
    # General intents
    GENERAL_QUESTION = "general_question"
    HELP_REQUEST = "help_request"
    GREETING = "greeting"
    UNKNOWN = "unknown"


@dataclass
class Entity:
    """Represents an extracted named entity."""
    text: str
    label: str
    start: int
    end: int
    confidence: float = 1.0
    normalized_value: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpatialScope:
    """Represents spatial parameters extracted from query."""
    locations: List[str] = field(default_factory=list)
    coordinates: Optional[Tuple[float, float, float, float]] = None  # bbox
    regions: List[str] = field(default_factory=list)
    ocean_basins: List[str] = field(default_factory=list)


@dataclass
class TemporalScope:
    """Represents temporal parameters extracted from query."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    relative_time: Optional[str] = None
    duration: Optional[str] = None
    time_expressions: List[str] = field(default_factory=list)


@dataclass
class ParameterScope:
    """Represents oceanographic parameters of interest."""
    measurements: List[str] = field(default_factory=list)
    depth_range: Optional[Tuple[float, float]] = None
    quality_requirements: List[str] = field(default_factory=list)
    data_mode: Optional[str] = None


@dataclass
class QueryAnalysis:
    """Complete analysis of a natural language query."""
    original_query: str
    language: str
    intent: QueryIntent
    confidence: float
    entities: List[Entity]
    spatial_scope: SpatialScope
    temporal_scope: TemporalScope
    parameter_scope: ParameterScope
    disambiguation_needed: bool = False
    clarification_questions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntentClassifier:
    """Classify user intents for oceanographic queries."""
    
    def __init__(self):
        self.intent_patterns = self._initialize_intent_patterns()
        self.intent_keywords = self._initialize_intent_keywords()
    
    def _initialize_intent_patterns(self) -> Dict[QueryIntent, List[str]]:
        """Initialize regex patterns for intent classification."""
        return {
            QueryIntent.GET_FLOAT_INFO: [
                r"(?i)\b(show|get|find|tell me about|information about)\s+float\s+(\d+)",
                r"(?i)\bfloat\s+(\d+)\s+(info|details|data)",
                r"(?i)\bwhat\s+is\s+float\s+(\d+)",
            ],
            
            QueryIntent.GET_PROFILES: [
                r"(?i)\b(show|get|list)\s+(profiles?|measurements?)\s+from",
                r"(?i)\bprofiles?\s+(for|from|of)\s+",
                r"(?i)\bhow many profiles",
            ],
            
            QueryIntent.SEARCH_FLOATS: [
                r"(?i)\b(find|search|locate)\s+floats?\s+(in|near|around)",
                r"(?i)\bfloats?\s+(in|near|around)\s+",
                r"(?i)\bwhich floats\s+",
            ],
            
            QueryIntent.ANALYZE_TEMPERATURE: [
                r"(?i)\b(temperature|temp)\s+(analysis|trend|pattern|variation)",
                r"(?i)\b(analyze|examine|study)\s+temperature",
                r"(?i)\bhow\s+(hot|cold|warm)\s+is",
                r"(?i)\btemperature\s+(change|variation|anomaly)",
            ],
            
            QueryIntent.ANALYZE_SALINITY: [
                r"(?i)\b(salinity|salt)\s+(analysis|trend|pattern|variation)",
                r"(?i)\b(analyze|examine|study)\s+salinity",
                r"(?i)\bhow\s+salty\s+is",
                r"(?i)\bsalinity\s+(change|variation|anomaly)",
            ],
            
            QueryIntent.SHOW_MAP: [
                r"(?i)\b(show|display|plot)\s+(on\s+)?(map|chart)",
                r"(?i)\bmap\s+(of|showing|with)",
                r"(?i)\b(where|location)\s+",
                r"(?i)\b(visualize|plot)\s+.*(location|position|geography)",
            ],
            
            QueryIntent.PLOT_PROFILE: [
                r"(?i)\b(plot|graph|chart|show)\s+profile",
                r"(?i)\bprofile\s+(plot|graph|chart)",
                r"(?i)\b(depth|pressure)\s+vs\s+(temperature|salinity)",
            ],
            
            QueryIntent.COMPARE_PROFILES: [
                r"(?i)\b(compare|comparison)\s+",
                r"(?i)\bdifference\s+between",
                r"(?i)\bhow\s+different\s+",
                r"(?i)\bversus\s+|vs\s+",
            ],
            
            QueryIntent.HELP_REQUEST: [
                r"(?i)\b(help|how\s+to|what\s+can|tutorial|guide)",
                r"(?i)\bcan\s+you\s+(help|show|teach)",
                r"(?i)\bi\s+don't\s+know\s+how",
            ],
            
            QueryIntent.GREETING: [
                r"(?i)\b(hello|hi|hey|greetings|good\s+(morning|afternoon|evening))",
                r"(?i)\bnamaste\b",
                r"(?i)\bwhat\s+can\s+you\s+do",
            ],
        }
    
    def _initialize_intent_keywords(self) -> Dict[QueryIntent, List[str]]:
        """Initialize keyword lists for intent classification."""
        return {
            QueryIntent.GET_FLOAT_INFO: [
                "float", "platform", "wmo", "deployment", "status"
            ],
            QueryIntent.GET_PROFILES: [
                "profile", "measurement", "data", "cycle", "dive"
            ],
            QueryIntent.ANALYZE_TEMPERATURE: [
                "temperature", "temp", "thermal", "heat", "warm", "cold"
            ],
            QueryIntent.ANALYZE_SALINITY: [
                "salinity", "salt", "psu", "practical salinity"
            ],
            QueryIntent.ANALYZE_OXYGEN: [
                "oxygen", "o2", "dissolved oxygen", "doxy"
            ],
            QueryIntent.SHOW_MAP: [
                "map", "location", "position", "coordinates", "where"
            ],
            QueryIntent.PLOT_PROFILE: [
                "plot", "graph", "chart", "profile", "depth", "pressure"
            ],
        }
    
    def classify_intent(self, query: str) -> Tuple[QueryIntent, float]:
        """
        Classify the intent of a query.
        
        Returns:
            Tuple of (intent, confidence_score)
        """
        query_lower = query.lower()
        intent_scores = {}
        
        # Pattern-based classification
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    intent_scores[intent] = intent_scores.get(intent, 0) + 0.8
        
        # Keyword-based classification
        for intent, keywords in self.intent_keywords.items():
            keyword_count = sum(1 for keyword in keywords if keyword in query_lower)
            if keyword_count > 0:
                score = min(keyword_count * 0.2, 0.6)
                intent_scores[intent] = intent_scores.get(intent, 0) + score
        
        # Return highest scoring intent
        if intent_scores:
            best_intent = max(intent_scores.items(), key=lambda x: x[1])
            return best_intent[0], min(best_intent[1], 1.0)
        
        return QueryIntent.UNKNOWN, 0.0


class EntityExtractor:
    """Extract oceanographic entities from natural language."""
    
    def __init__(self):
        # Load spaCy model (English)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy English model not found, using basic tokenizer")
            self.nlp = None
        
        self.matcher = None
        if self.nlp:
            self.matcher = Matcher(self.nlp.vocab)
            self._initialize_patterns()
        
        self.oceanographic_entities = self._initialize_oceanographic_entities()
    
    def _initialize_patterns(self):
        """Initialize spaCy matcher patterns for oceanographic entities."""
        
        # Float ID patterns
        self.matcher.add("FLOAT_ID", [
            [{"TEXT": {"REGEX": r"\d{7,10}"}}],  # WMO IDs
            [{"LOWER": "float"}, {"TEXT": {"REGEX": r"\d+"}}],
        ])
        
        # Coordinate patterns
        self.matcher.add("COORDINATES", [
            [{"TEXT": {"REGEX": r"-?\d+\.?\d*"}}, {"TEXT": "°"}, 
             {"LOWER": {"IN": ["n", "s", "north", "south"]}},
             {"TEXT": {"REGEX": r"-?\d+\.?\d*"}}, {"TEXT": "°"}, 
             {"LOWER": {"IN": ["e", "w", "east", "west"]}}],
        ])
        
        # Date patterns
        self.matcher.add("DATE", [
            [{"TEXT": {"REGEX": r"\d{1,2}"}}, {"TEXT": "/"}, 
             {"TEXT": {"REGEX": r"\d{1,2}"}}, {"TEXT": "/"}, 
             {"TEXT": {"REGEX": r"\d{4}"}}],
            [{"TEXT": {"REGEX": r"\d{4}"}}, {"TEXT": "-"}, 
             {"TEXT": {"REGEX": r"\d{1,2}"}}, {"TEXT": "-"}, 
             {"TEXT": {"REGEX": r"\d{1,2}"}}],
        ])
        
        # Measurement parameters
        self.matcher.add("PARAMETER", [
            [{"LOWER": {"IN": ["temperature", "temp", "thermal"]}}],
            [{"LOWER": {"IN": ["salinity", "salt", "psu"]}}],
            [{"LOWER": {"IN": ["oxygen", "o2", "dissolved_oxygen", "doxy"]}}],
            [{"LOWER": {"IN": ["pressure", "depth", "level"]}}],
            [{"LOWER": {"IN": ["nitrate", "no3", "nitrogen"]}}],
            [{"LOWER": {"IN": ["ph", "acidity", "alkalinity"]}}],
            [{"LOWER": {"IN": ["chlorophyll", "chla", "chl-a"]}}],
        ])
        
        # Ocean regions
        self.matcher.add("OCEAN_REGION", [
            [{"LOWER": {"IN": ["atlantic", "pacific", "indian", "arctic", "southern"]}}],
            [{"LOWER": "bay"}, {"LOWER": "of"}, {"LOWER": "bengal"}],
            [{"LOWER": "arabian"}, {"LOWER": "sea"}],
            [{"LOWER": "mediterranean"}, {"LOWER": "sea"}],
        ])
    
    def _initialize_oceanographic_entities(self) -> Dict[str, List[str]]:
        """Initialize oceanographic entity vocabularies."""
        return {
            "parameters": [
                "temperature", "temp", "thermal",
                "salinity", "salt", "psu", "practical salinity",
                "oxygen", "o2", "dissolved oxygen", "doxy",
                "pressure", "depth", "level",
                "nitrate", "no3", "nitrogen",
                "ph", "acidity", "alkalinity",
                "chlorophyll", "chla", "chl-a", "chlorophyll-a"
            ],
            "ocean_basins": [
                "atlantic", "pacific", "indian", "arctic", "southern",
                "north atlantic", "south atlantic", "north pacific", "south pacific"
            ],
            "regions": [
                "bay of bengal", "arabian sea", "mediterranean sea",
                "caribbean sea", "north sea", "baltic sea"
            ],
            "quality_flags": [
                "good", "probably good", "probably bad", "bad",
                "real-time", "adjusted", "delayed mode"
            ],
            "time_expressions": [
                "today", "yesterday", "last week", "last month", "last year",
                "recent", "lately", "currently", "now"
            ]
        }
    
    def extract_entities(self, query: str) -> List[Entity]:
        """Extract entities from query text."""
        entities = []
        
        if self.nlp and self.matcher:
            doc = self.nlp(query)
            
            # Extract using spaCy NER
            for ent in doc.ents:
                entities.append(Entity(
                    text=ent.text,
                    label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=0.8,
                    metadata={"source": "spacy_ner"}
                ))
            
            # Extract using custom patterns
            matches = self.matcher(doc)
            for match_id, start, end in matches:
                label = self.nlp.vocab.strings[match_id]
                span = doc[start:end]
                entities.append(Entity(
                    text=span.text,
                    label=label,
                    start=span.start_char,
                    end=span.end_char,
                    confidence=0.9,
                    metadata={"source": "pattern_matching"}
                ))
        
        # Extract using keyword matching
        entities.extend(self._extract_by_keywords(query))
        
        # Remove overlapping entities
        entities = self._remove_overlapping_entities(entities)
        
        return entities
    
    def _extract_by_keywords(self, query: str) -> List[Entity]:
        """Extract entities using keyword matching."""
        entities = []
        query_lower = query.lower()
        
        for category, keywords in self.oceanographic_entities.items():
            for keyword in keywords:
                start = query_lower.find(keyword)
                if start != -1:
                    entities.append(Entity(
                        text=keyword,
                        label=category.upper(),
                        start=start,
                        end=start + len(keyword),
                        confidence=0.7,
                        metadata={"source": "keyword_matching", "category": category}
                    ))
        
        return entities
    
    def _remove_overlapping_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove overlapping entities, keeping higher confidence ones."""
        if not entities:
            return entities
        
        # Sort by start position
        entities.sort(key=lambda e: e.start)
        
        filtered_entities = []
        for entity in entities:
            # Check for overlap with already selected entities
            overlaps = False
            for selected in filtered_entities:
                if (entity.start < selected.end and entity.end > selected.start):
                    # Overlapping - keep the one with higher confidence
                    if entity.confidence > selected.confidence:
                        filtered_entities.remove(selected)
                        break
                    else:
                        overlaps = True
                        break
            
            if not overlaps:
                filtered_entities.append(entity)
        
        return filtered_entities


class ParameterParser:
    """Parse and extract oceanographic parameters from queries."""
    
    def __init__(self):
        self.spatial_patterns = self._initialize_spatial_patterns()
        self.temporal_patterns = self._initialize_temporal_patterns()
        self.parameter_patterns = self._initialize_parameter_patterns()
    
    def _initialize_spatial_patterns(self) -> Dict[str, str]:
        """Initialize patterns for spatial parameter extraction."""
        return {
            "coordinates": r"(-?\d+\.?\d*)\s*°?\s*([NS])\s*,?\s*(-?\d+\.?\d*)\s*°?\s*([EW])",
            "bbox": r"between\s+(-?\d+\.?\d*)\s*°?\s*and\s+(-?\d+\.?\d*)\s*°?\s*([NS])",
            "radius": r"within\s+(\d+)\s*(km|miles|degrees)\s+of",
            "depth_range": r"(\d+)\s*-\s*(\d+)\s*(m|meters|dbar)",
        }
    
    def _initialize_temporal_patterns(self) -> Dict[str, str]:
        """Initialize patterns for temporal parameter extraction."""
        return {
            "date_range": r"(\d{4}-\d{1,2}-\d{1,2})\s+to\s+(\d{4}-\d{1,2}-\d{1,2})",
            "year": r"in\s+(\d{4})|(\d{4})",
            "month_year": r"(\w+)\s+(\d{4})",
            "relative_time": r"(last|past|recent)\s+(\d+)\s+(days?|weeks?|months?|years?)",
            "season": r"(spring|summer|fall|autumn|winter)\s+(\d{4})?",
        }
    
    def _initialize_parameter_patterns(self) -> Dict[str, str]:
        """Initialize patterns for parameter extraction."""
        return {
            "temperature_range": r"temperature\s+(between|from)\s+(-?\d+\.?\d*)\s*(to|and)\s+(-?\d+\.?\d*)",
            "salinity_range": r"salinity\s+(between|from)\s+(\d+\.?\d*)\s*(to|and)\s+(\d+\.?\d*)",
            "depth_specific": r"at\s+(\d+)\s*(m|meters|dbar)\s+depth",
            "quality_requirement": r"(good|high)\s+quality\s+data",
        }
    
    def parse_spatial_scope(self, query: str, entities: List[Entity]) -> SpatialScope:
        """Parse spatial parameters from query."""
        spatial_scope = SpatialScope()
        
        # Extract locations from entities
        for entity in entities:
            if entity.label in ["GPE", "LOC", "OCEAN_REGION"]:
                if "ocean" in entity.text.lower() or "sea" in entity.text.lower():
                    spatial_scope.ocean_basins.append(entity.text)
                else:
                    spatial_scope.locations.append(entity.text)
        
        # Extract coordinates using patterns
        for pattern_name, pattern in self.spatial_patterns.items():
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                if pattern_name == "coordinates":
                    lat, lat_dir, lon, lon_dir = match.groups()
                    lat_val = float(lat) * (-1 if lat_dir.upper() == 'S' else 1)
                    lon_val = float(lon) * (-1 if lon_dir.upper() == 'W' else 1)
                    # Create a small bbox around the point
                    spatial_scope.coordinates = (
                        lon_val - 0.5, lat_val - 0.5,
                        lon_val + 0.5, lat_val + 0.5
                    )
        
        return spatial_scope
    
    def parse_temporal_scope(self, query: str, entities: List[Entity]) -> TemporalScope:
        """Parse temporal parameters from query."""
        temporal_scope = TemporalScope()
        
        # Extract dates from entities
        for entity in entities:
            if entity.label in ["DATE", "TIME"]:
                temporal_scope.time_expressions.append(entity.text)
        
        # Extract using patterns
        for pattern_name, pattern in self.temporal_patterns.items():
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                if pattern_name == "date_range":
                    start_date_str, end_date_str = match.groups()
                    try:
                        temporal_scope.start_date = datetime.strptime(
                            start_date_str, "%Y-%m-%d"
                        ).date()
                        temporal_scope.end_date = datetime.strptime(
                            end_date_str, "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        pass
                
                elif pattern_name == "year":
                    year = int(match.group(1) or match.group(2))
                    temporal_scope.start_date = date(year, 1, 1)
                    temporal_scope.end_date = date(year, 12, 31)
                
                elif pattern_name == "relative_time":
                    time_unit = match.group(3)
                    amount = int(match.group(2))
                    
                    end_date = date.today()
                    if "day" in time_unit:
                        start_date = end_date - timedelta(days=amount)
                    elif "week" in time_unit:
                        start_date = end_date - timedelta(weeks=amount)
                    elif "month" in time_unit:
                        start_date = end_date - timedelta(days=amount * 30)
                    elif "year" in time_unit:
                        start_date = end_date - timedelta(days=amount * 365)
                    else:
                        continue
                    
                    temporal_scope.start_date = start_date
                    temporal_scope.end_date = end_date
                    temporal_scope.relative_time = match.group(0)
        
        return temporal_scope
    
    def parse_parameter_scope(self, query: str, entities: List[Entity]) -> ParameterScope:
        """Parse parameter requirements from query."""
        parameter_scope = ParameterScope()
        
        # Extract parameters from entities
        for entity in entities:
            if entity.label == "PARAMETERS":
                parameter_scope.measurements.append(entity.text.lower())
        
        # Extract using patterns
        for pattern_name, pattern in self.parameter_patterns.items():
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                if pattern_name == "depth_specific":
                    depth = float(match.group(1))
                    parameter_scope.depth_range = (depth - 10, depth + 10)
                elif pattern_name == "quality_requirement":
                    parameter_scope.quality_requirements.append("high_quality")
        
        return parameter_scope


class MultilingualProcessor:
    """Handle multilingual queries and responses."""
    
    def __init__(self):
        # Initialize best available translator backend
        self.translator_backend = "noop"
        self.translator = None

        if DeepTranslator is not None:
            self.translator_backend = "deep_translator"
        elif GoogleTransTranslator is not None:
            try:
                self.translator = GoogleTransTranslator()
                self.translator_backend = "googletrans"
            except Exception:
                self.translator_backend = "noop"
        self.supported_languages = ["en", "hi"]  # English, Hindi
        self.language_names = {
            "en": "English",
            "hi": "Hindi",
            "auto": "Auto-detect"
        }
    
    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detect language of input text.
        
        Returns:
            Tuple of (language_code, confidence)
        """
        try:
            detections = detect_langs(text)
            if detections:
                best_detection = detections[0]
                return best_detection.lang, best_detection.prob
        except:
            pass
        
        return "en", 0.5  # Default to English
    
    def translate_text(
        self, 
        text: str, 
        target_language: str = "en",
        source_language: str = "auto"
    ) -> str:
        """Translate text to target language."""
        try:
            if source_language == target_language:
                return text

            if self.translator_backend == "deep_translator":
                # deep_translator constructs translator per call
                return DeepTranslator(source=source_language, target=target_language).translate(text)  # type: ignore

            if self.translator_backend == "googletrans" and self.translator is not None:
                result = self.translator.translate(
                    text,
                    src=source_language,
                    dest=target_language,
                )
                return result.text

            # No translator available → graceful no-op
            return text
        
        except Exception as e:
            logger.warning(
                "Translation failed",
                error=str(e),
                source_lang=source_language,
                target_lang=target_language
            )
            return text  # Return original text if translation fails
    
    def is_supported_language(self, language_code: str) -> bool:
        """Check if language is supported."""
        return language_code in self.supported_languages


class DisambiguationEngine:
    """Generate clarifying questions for ambiguous queries."""
    
    def __init__(self):
        self.disambiguation_templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, List[str]]:
        """Initialize templates for clarifying questions."""
        return {
            "missing_location": [
                "Which ocean region are you interested in?",
                "Could you specify the location or coordinates?",
                "Are you looking at a specific area like the Bay of Bengal or Arabian Sea?"
            ],
            "missing_time": [
                "What time period are you interested in?",
                "Are you looking at recent data or a specific year/month?",
                "Should I look at the latest available data?"
            ],
            "missing_parameter": [
                "Which measurement parameter are you interested in - temperature, salinity, or oxygen?",
                "What specific data would you like to analyze?",
                "Are you looking at surface or deep water measurements?"
            ],
            "ambiguous_intent": [
                "Would you like me to show this data on a map or create a chart?",
                "Are you looking for specific float information or regional analysis?",
                "Should I search for floats or analyze existing data?"
            ]
        }
    
    def generate_clarification_questions(
        self, 
        analysis: QueryAnalysis
    ) -> List[str]:
        """Generate clarifying questions based on query analysis."""
        questions = []
        
        # Check for missing spatial information
        if (analysis.intent in [QueryIntent.SEARCH_FLOATS, QueryIntent.SHOW_MAP] and 
            not analysis.spatial_scope.locations and 
            not analysis.spatial_scope.coordinates):
            questions.extend(self.disambiguation_templates["missing_location"])
        
        # Check for missing temporal information
        if (analysis.intent in [QueryIntent.ANALYZE_TEMPERATURE, QueryIntent.TREND_ANALYSIS] and
            not analysis.temporal_scope.start_date and
            not analysis.temporal_scope.relative_time):
            questions.extend(self.disambiguation_templates["missing_time"])
        
        # Check for missing parameter information
        if (analysis.intent == QueryIntent.GENERAL_QUESTION and
            not analysis.parameter_scope.measurements):
            questions.extend(self.disambiguation_templates["missing_parameter"])
        
        # Check for ambiguous intent
        if analysis.confidence < 0.6:
            questions.extend(self.disambiguation_templates["ambiguous_intent"])
        
        return questions[:2]  # Return max 2 questions


class NLUService:
    """Main Natural Language Understanding service."""
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.parameter_parser = ParameterParser()
        self.multilingual_processor = MultilingualProcessor()
        self.disambiguation_engine = DisambiguationEngine()
        self.settings = get_settings()
    
    async def analyze_query(
        self, 
        query: str,
        user_language: str = "auto",
        correlation_id: str = None
    ) -> QueryAnalysis:
        """
        Perform complete analysis of a natural language query.
        
        Args:
            query: User's natural language query
            user_language: User's preferred language
            correlation_id: Request correlation ID
            
        Returns:
            Complete query analysis
        """
        try:
            logger.info(
                "Analyzing query with NLU",
                query_length=len(query),
                user_language=user_language,
                correlation_id=correlation_id
            )
            
            # Detect language
            detected_language, lang_confidence = self.multilingual_processor.detect_language(query)
            
            # Translate to English if needed for processing
            english_query = query
            if detected_language != "en":
                english_query = self.multilingual_processor.translate_text(
                    query, target_language="en", source_language=detected_language
                )
            
            # Extract entities
            entities = self.entity_extractor.extract_entities(english_query)
            
            # Classify intent
            intent, intent_confidence = self.intent_classifier.classify_intent(english_query)
            
            # Parse parameters
            spatial_scope = self.parameter_parser.parse_spatial_scope(english_query, entities)
            temporal_scope = self.parameter_parser.parse_temporal_scope(english_query, entities)
            parameter_scope = self.parameter_parser.parse_parameter_scope(english_query, entities)
            
            # Create analysis result
            analysis = QueryAnalysis(
                original_query=query,
                language=detected_language,
                intent=intent,
                confidence=intent_confidence,
                entities=entities,
                spatial_scope=spatial_scope,
                temporal_scope=temporal_scope,
                parameter_scope=parameter_scope,
                metadata={
                    "language_confidence": lang_confidence,
                    "english_query": english_query if english_query != query else None,
                    "processing_timestamp": datetime.utcnow().isoformat(),
                    "correlation_id": correlation_id
                }
            )
            
            # Check if disambiguation is needed
            clarification_questions = self.disambiguation_engine.generate_clarification_questions(analysis)
            if clarification_questions:
                analysis.disambiguation_needed = True
                analysis.clarification_questions = clarification_questions
            
            logger.info(
                "Query analysis completed",
                intent=intent.value,
                confidence=intent_confidence,
                entities_count=len(entities),
                disambiguation_needed=analysis.disambiguation_needed,
                correlation_id=correlation_id
            )
            
            return analysis
            
        except Exception as e:
            logger.error(
                "Query analysis failed",
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            
            # Return basic analysis on error
            return QueryAnalysis(
                original_query=query,
                language="en",
                intent=QueryIntent.UNKNOWN,
                confidence=0.0,
                entities=[],
                spatial_scope=SpatialScope(),
                temporal_scope=TemporalScope(),
                parameter_scope=ParameterScope(),
                metadata={"error": str(e), "correlation_id": correlation_id}
            )
    
    def extract_query_parameters(self, analysis: QueryAnalysis) -> Dict[str, Any]:
        """Extract structured parameters for database queries."""
        parameters = {
            "intent": analysis.intent.value,
            "confidence": analysis.confidence,
            "language": analysis.language
        }
        
        # Spatial parameters
        if analysis.spatial_scope.coordinates:
            parameters["bbox"] = analysis.spatial_scope.coordinates
        if analysis.spatial_scope.locations:
            parameters["locations"] = analysis.spatial_scope.locations
        if analysis.spatial_scope.ocean_basins:
            parameters["ocean_basins"] = analysis.spatial_scope.ocean_basins
        
        # Temporal parameters
        if analysis.temporal_scope.start_date:
            parameters["start_date"] = analysis.temporal_scope.start_date.isoformat()
        if analysis.temporal_scope.end_date:
            parameters["end_date"] = analysis.temporal_scope.end_date.isoformat()
        if analysis.temporal_scope.relative_time:
            parameters["relative_time"] = analysis.temporal_scope.relative_time
        
        # Parameter scope
        if analysis.parameter_scope.measurements:
            parameters["measurements"] = analysis.parameter_scope.measurements
        if analysis.parameter_scope.depth_range:
            parameters["depth_range"] = analysis.parameter_scope.depth_range
        if analysis.parameter_scope.quality_requirements:
            parameters["quality_requirements"] = analysis.parameter_scope.quality_requirements
        
        # Entity information
        parameters["entities"] = [
            {
                "text": entity.text,
                "label": entity.label,
                "confidence": entity.confidence
            }
            for entity in analysis.entities
        ]
        
        return parameters
