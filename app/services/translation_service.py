"""
Translation and Multilingual Support Service for FloatChat.

Provides comprehensive language support including:
- Text translation between supported languages
- Language detection and validation
- Regional language support for Indian languages
- Integration with voice processing for multilingual conversations
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import re

# Translation dependencies (optional)
try:
    from googletrans import Translator
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0  # For consistent results
    TRANSLATION_DEPS_AVAILABLE = True
except ImportError:
    TRANSLATION_DEPS_AVAILABLE = False

from app.core.config import get_settings
from app.utils.exceptions import TranslationError
from app.models.schemas import LanguageDetectionResponse

settings = get_settings()
logger = logging.getLogger(__name__)


class SupportedLanguage(Enum):
    """Enumeration of supported languages with metadata."""
    
    # Major Indian Languages
    ENGLISH = ("en", "English", "English", "en-US", True)
    HINDI = ("hi", "Hindi", "हिन्दी", "hi-IN", True)
    BENGALI = ("bn", "Bengali", "বাংলা", "bn-IN", True)
    TELUGU = ("te", "Telugu", "తెలుగు", "te-IN", True)
    TAMIL = ("ta", "Tamil", "தமிழ்", "ta-IN", True)
    MARATHI = ("mr", "Marathi", "मराठी", "mr-IN", True)
    GUJARATI = ("gu", "Gujarati", "ગુજરાતી", "gu-IN", True)
    KANNADA = ("kn", "Kannada", "ಕನ್ನಡ", "kn-IN", True)
    MALAYALAM = ("ml", "Malayalam", "മലയാളം", "ml-IN", True)
    ODIA = ("or", "Odia", "ଓଡ଼ିଆ", "or-IN", True)
    PUNJABI = ("pa", "Punjabi", "ਪੰਜਾਬੀ", "pa-IN", True)
    ASSAMESE = ("as", "Assamese", "অসমীয়া", "as-IN", True)
    
    # Additional languages that might be useful for oceanographic research
    URDU = ("ur", "Urdu", "اردو", "ur-IN", False)
    SANSKRIT = ("sa", "Sanskrit", "संस्कृत", "sa-IN", False)
    
    def __init__(self, code: str, lang_name: str, native_name: str, locale: str, voice_supported: bool):
        self.code = code
        self.lang_name = lang_name  # Changed from 'name' to avoid conflict
        self.native_name = native_name
        self.locale = locale
        self.voice_supported = voice_supported


class LanguageDetector:
    """Language detection service."""
    
    def __init__(self):
        self.supported_codes = [lang.code for lang in SupportedLanguage]
        
        # Patterns for script-based detection (fallback)
        self.script_patterns = {
            'hi': re.compile(r'[\u0900-\u097F]+'),  # Devanagari
            'bn': re.compile(r'[\u0980-\u09FF]+'),  # Bengali
            'te': re.compile(r'[\u0C00-\u0C7F]+'),  # Telugu
            'ta': re.compile(r'[\u0B80-\u0BFF]+'),  # Tamil
            'mr': re.compile(r'[\u0900-\u097F]+'),  # Devanagari (same as Hindi)
            'gu': re.compile(r'[\u0A80-\u0AFF]+'),  # Gujarati
            'kn': re.compile(r'[\u0C80-\u0CFF]+'),  # Kannada
            'ml': re.compile(r'[\u0D00-\u0D7F]+'),  # Malayalam
            'or': re.compile(r'[\u0B00-\u0B7F]+'),  # Odia
            'pa': re.compile(r'[\u0A00-\u0A7F]+'),  # Gurmukhi
            'as': re.compile(r'[\u0980-\u09FF]+'),  # Bengali script (same as Bengali)
        }
    
    async def detect_language(self, text: str) -> LanguageDetectionResponse:
        """
        Detect language from text input.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language detection result
        """
        if not text or not text.strip():
            return LanguageDetectionResponse(
                detected_language="en",
                confidence=0.0,
                supported=True
            )
        
        try:
            # Try using langdetect if available
            if TRANSLATION_DEPS_AVAILABLE:
                detected = detect(text)
                confidence = 0.9  # langdetect doesn't provide confidence
            else:
                # Fallback to script-based detection
                detected, confidence = self._detect_by_script(text)
            
            # Validate against supported languages
            if detected not in self.supported_codes:
                detected = "en"  # Default to English
                confidence = 0.5
            
            return LanguageDetectionResponse(
                detected_language=detected,
                confidence=confidence,
                supported=detected in self.supported_codes
            )
            
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return LanguageDetectionResponse(
                detected_language="en",
                confidence=0.5,
                supported=True
            )
    
    def _detect_by_script(self, text: str) -> Tuple[str, float]:
        """
        Fallback language detection based on script patterns.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (language_code, confidence)
        """
        script_scores = {}
        
        for lang_code, pattern in self.script_patterns.items():
            matches = pattern.findall(text)
            if matches:
                # Calculate score based on character coverage
                script_chars = sum(len(match) for match in matches)
                total_chars = len(text)
                score = script_chars / total_chars if total_chars > 0 else 0
                script_scores[lang_code] = score
        
        if script_scores:
            # Return language with highest script coverage
            best_lang = max(script_scores, key=script_scores.get)
            confidence = script_scores[best_lang]
            return best_lang, confidence
        else:
            # Default to English if no scripts detected
            return "en", 0.8


class TranslationEngine:
    """Text translation engine with caching."""
    
    def __init__(self):
        if TRANSLATION_DEPS_AVAILABLE:
            self.translator = Translator()
        else:
            self.translator = None
        
        # Translation cache to reduce API calls
        self.translation_cache: Dict[str, str] = {}
        self.cache_size_limit = 1000
        
        # Common oceanographic terms and their translations
        self.domain_terms = {
            'en': {
                'temperature': 'temperature',
                'salinity': 'salinity',
                'pressure': 'pressure',
                'depth': 'depth',
                'ocean': 'ocean',
                'sea': 'sea',
                'float': 'float',
                'profile': 'profile',
                'measurement': 'measurement'
            },
            'hi': {
                'temperature': 'तापमान',
                'salinity': 'लवणता',
                'pressure': 'दबाव',
                'depth': 'गहराई',
                'ocean': 'महासागर',
                'sea': 'सागर',
                'float': 'फ्लोट',
                'profile': 'प्रोफ़ाइल',
                'measurement': 'मापन'
            }
            # Add more languages as needed
        }
    
    async def translate_text(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> str:
        """
        Translate text between languages.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated text
        """
        # Skip translation if same language
        if source_lang == target_lang:
            return text
        
        # Check cache first
        cache_key = f"{source_lang}:{target_lang}:{hash(text)}"
        if cache_key in self.translation_cache:
            return self.translation_cache[cache_key]
        
        try:
            if not TRANSLATION_DEPS_AVAILABLE:
                # Fallback: try domain-specific translation
                translated = self._translate_domain_terms(text, source_lang, target_lang)
                if translated != text:
                    return translated
                
                raise TranslationError("Translation service not available")
            
            # Use Google Translate
            result = await self._google_translate(text, source_lang, target_lang)
            
            # Cache the result
            if len(self.translation_cache) < self.cache_size_limit:
                self.translation_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            # Return original text if translation fails
            return text
    
    async def _google_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Perform Google Translate API call."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.translator.translate(text, src=source_lang, dest=target_lang)
        )
        return result.text
    
    def _translate_domain_terms(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Fallback translation using domain-specific terms.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated text (or original if no matches)
        """
        if source_lang not in self.domain_terms or target_lang not in self.domain_terms:
            return text
        
        source_terms = self.domain_terms[source_lang]
        target_terms = self.domain_terms[target_lang]
        
        translated_text = text.lower()
        
        # Replace known terms
        for en_term, source_term in source_terms.items():
            if source_term.lower() in translated_text:
                target_term = target_terms.get(en_term, source_term)
                translated_text = translated_text.replace(source_term.lower(), target_term)
        
        return translated_text if translated_text != text.lower() else text


class MultilingualService:
    """
    Main multilingual service for FloatChat.
    
    Provides comprehensive language support including detection,
    translation, and integration with other services.
    """
    
    def __init__(self):
        self.language_detector = LanguageDetector()
        self.translation_engine = TranslationEngine()
        
        # Cache for language preferences
        self.user_language_preferences: Dict[str, str] = {}
        
        logger.info(f"MultilingualService initialized with translation support: {TRANSLATION_DEPS_AVAILABLE}")
    
    def get_supported_languages(self) -> List[Dict[str, Any]]:
        """
        Get list of all supported languages.
        
        Returns:
            List of language information
        """
        languages = []
        for lang in SupportedLanguage:
            languages.append({
                'code': lang.code,
                'name': lang.lang_name,
                'native_name': lang.native_name,
                'locale': lang.locale,
                'voice_supported': lang.voice_supported
            })
        
        return languages
    
    async def detect_language(self, text: str) -> LanguageDetectionResponse:
        """
        Detect language from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language detection result
        """
        return await self.language_detector.detect_language(text)
    
    async def translate_text(
        self, 
        text: str, 
        target_language: str,
        source_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Translate text to target language.
        
        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (auto-detect if None)
            
        Returns:
            Translation result with metadata
        """
        try:
            # Detect source language if not provided
            if not source_language:
                detection = await self.detect_language(text)
                source_language = detection.detected_language
            
            # Perform translation
            translated_text = await self.translation_engine.translate_text(
                text, source_language, target_language
            )
            
            return {
                'original_text': text,
                'translated_text': translated_text,
                'source_language': source_language,
                'target_language': target_language,
                'translation_available': TRANSLATION_DEPS_AVAILABLE
            }
            
        except Exception as e:
            logger.error(f"Translation service error: {e}")
            return {
                'original_text': text,
                'translated_text': text,  # Return original if translation fails
                'source_language': source_language or 'unknown',
                'target_language': target_language,
                'translation_available': False,
                'error': str(e)
            }
    
    async def process_multilingual_query(
        self, 
        query: str, 
        user_language: str = "en"
    ) -> Dict[str, Any]:
        """
        Process a multilingual query for the chat system.
        
        Args:
            query: User query in any supported language
            user_language: User's preferred language
            
        Returns:
            Processed query information
        """
        # Detect query language
        detection = await self.detect_language(query)
        query_language = detection.detected_language
        
        # Translate to English for processing if needed
        english_query = query
        if query_language != 'en':
            translation = await self.translate_text(query, 'en', query_language)
            english_query = translation['translated_text']
        
        return {
            'original_query': query,
            'english_query': english_query,
            'detected_language': query_language,
            'user_language': user_language,
            'needs_translation': query_language != 'en',
            'detection_confidence': detection.confidence
        }
    
    async def format_response_for_language(
        self, 
        response: str, 
        target_language: str
    ) -> Dict[str, Any]:
        """
        Format response for specific language.
        
        Args:
            response: Response text in English
            target_language: Target language for response
            
        Returns:
            Formatted response with translation
        """
        if target_language == 'en':
            return {
                'response': response,
                'language': 'en',
                'translated': False
            }
        
        # Translate response to target language
        translation = await self.translate_text(response, target_language, 'en')
        
        return {
            'response': translation['translated_text'],
            'original_response': response,
            'language': target_language,
            'translated': True,
            'translation_quality': 'good' if TRANSLATION_DEPS_AVAILABLE else 'limited'
        }
    
    def validate_language_code(self, language_code: str) -> bool:
        """
        Validate if language code is supported.
        
        Args:
            language_code: Language code to validate
            
        Returns:
            True if supported, False otherwise
        """
        supported_codes = [lang.code for lang in SupportedLanguage]
        return language_code in supported_codes
    
    def get_language_info(self, language_code: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a language.
        
        Args:
            language_code: Language code
            
        Returns:
            Language information or None if not found
        """
        for lang in SupportedLanguage:
            if lang.code == language_code:
                return {
                    'code': lang.code,
                    'name': lang.lang_name,
                    'native_name': lang.native_name,
                    'locale': lang.locale,
                    'voice_supported': lang.voice_supported
                }
        return None


# Service instance
multilingual_service = MultilingualService()
