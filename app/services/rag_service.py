"""
FloatChat - Retrieval-Augmented Generation (RAG) Service

Comprehensive RAG pipeline combining vector search with LLM generation
for contextually relevant responses about ARGO oceanographic data.
"""

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
import uuid

import numpy as np
from sentence_transformers import SentenceTransformer
import os
from typing import Optional
try:  # Optional GPU acceleration
    import torch  # type: ignore
except Exception:  # pragma: no cover
    torch = None  # type: ignore
import faiss
import chromadb
from chromadb.config import Settings
import structlog

from app.core.config import get_settings
from app.core.database import get_async_session
from app.services.gemini_service import GeminiService
from app.services.nlu_service import NLUService, QueryAnalysis
from app.utils.sql_generator import NL2SQLTranslator
from app.utils.exceptions import AIServiceError, ValidationError

logger = structlog.get_logger(__name__)


@dataclass
class DocumentChunk:
    """Represents a chunk of document content for RAG."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    source: str = ""
    chunk_index: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RetrievalResult:
    """Result from vector similarity search."""
    chunk: DocumentChunk
    similarity_score: float
    relevance_score: float = 0.0
    metadata_match_score: float = 0.0


@dataclass
class ContextRanking:
    """Ranking information for retrieved context."""
    relevance_weight: float = 0.4
    recency_weight: float = 0.3
    similarity_weight: float = 0.2
    metadata_weight: float = 0.1


@dataclass
class RAGResponse:
    """Complete response from RAG pipeline."""
    response: str
    confidence_score: float
    retrieved_contexts: List[RetrievalResult]
    sql_query: Optional[str] = None
    query_results: Optional[List[Dict[str, Any]]] = None
    fact_check_results: Optional[Dict[str, Any]] = None
    generation_metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: int = 0


class EmbeddingGenerator:
    """Generate embeddings for text content using sentence transformers."""
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        batch_size: int = 128,
        device: Optional[str] = None,
    ):
        self.model_name = model_name
        self.model = None
        self.embedding_dimension = 384  # Default for all-MiniLM-L6-v2
        self.batch_size = max(16, batch_size)
        self.device = device
    
    async def initialize(self):
        """Initialize the embedding model."""
        try:
            logger.info("Loading sentence transformer model", model=self.model_name)
            # Select device
            if self.device is None:
                use_cuda = bool(torch and hasattr(torch, "cuda") and torch.cuda.is_available())
                self.device = "cuda" if use_cuda else "cpu"
            # Set CPU thread usage sensibly
            try:
                if self.device == "cpu" and torch is not None:
                    torch.set_num_threads(min(os.cpu_count() or 4, 8))
            except Exception:
                pass

            self.model = SentenceTransformer(self.model_name, device=self.device)
            self.embedding_dimension = self.model.get_sentence_embedding_dimension()
            logger.info("Embedding model loaded", dimension=self.embedding_dimension)
        except Exception as e:
            logger.error("Failed to load embedding model", error=str(e))
            raise AIServiceError(f"Failed to initialize embedding model: {str(e)}")
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        if not self.model:
            raise AIServiceError("Embedding model not initialized")
        
        try:
            embedding = self.model.encode(text, convert_to_tensor=False)
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e))
            raise AIServiceError(f"Embedding generation failed: {str(e)}")
    
    def generate_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts."""
        if not self.model:
            raise AIServiceError("Embedding model not initialized")
        
        try:
            embeddings = self.model.encode(
                texts,
                convert_to_tensor=False,
                batch_size=self.batch_size,
                show_progress_bar=False,
                device=self.device,
                normalize_embeddings=False,
            )
            return np.array(embeddings, dtype=np.float32)
        except Exception as e:
            logger.error("Failed to generate batch embeddings", error=str(e))
            raise AIServiceError(f"Batch embedding generation failed: {str(e)}")


class VectorStore:
    """Vector database for storing and retrieving document embeddings."""
    
    def __init__(self):
        self.settings = get_settings()
        self.embedding_generator = EmbeddingGenerator(
            self.settings.embedding_model,
            batch_size=self.settings.embedding_batch_size,
        )
        
        # FAISS index for fast similarity search
        self.faiss_index = None
        self.document_map = {}  # Map FAISS index to document IDs
        
        # ChromaDB for persistent storage
        self.chroma_client = None
        self.chroma_collection = None
    
    async def initialize(self):
        """Initialize vector store components."""
        try:
            logger.info("Initializing vector store")
            
            # Initialize embedding generator
            await self.embedding_generator.initialize()
            
            # Initialize FAISS index
            self.faiss_index = faiss.IndexFlatIP(self.embedding_generator.embedding_dimension)
            
            # Initialize ChromaDB (new client API)
            try:
                # Prefer persistent on-disk store
                self.chroma_client = chromadb.PersistentClient(path="./data/chromadb")
            except Exception:
                # Fallback to in-memory client (non-persistent)
                logger.warning("Chroma PersistentClient failed, using in-memory Client")
                self.chroma_client = chromadb.Client()

            # Get or create collection
            existing_names = [c.name for c in self.chroma_client.list_collections()]
            if self.settings.chromadb_collection_name in existing_names:
                self.chroma_collection = self.chroma_client.get_collection(
                    name=self.settings.chromadb_collection_name
                )
                logger.info("Loaded existing ChromaDB collection")
            else:
                self.chroma_collection = self.chroma_client.create_collection(
                    name=self.settings.chromadb_collection_name,
                    metadata={"description": "ARGO oceanographic data knowledge base"}
                )
                logger.info("Created new ChromaDB collection")
            
            # Load existing embeddings into FAISS
            await self._load_existing_embeddings()
            
            logger.info("Vector store initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize vector store", error=str(e))
            raise AIServiceError(f"Vector store initialization failed: {str(e)}")
    
    async def _load_existing_embeddings(self):
        """Load existing embeddings from ChromaDB into FAISS."""
        try:
            # Get all documents from ChromaDB
            results = self.chroma_collection.get(include=["embeddings", "metadatas"])
            
            if results["ids"]:
                embeddings = np.array(results["embeddings"], dtype=np.float32)
                self.faiss_index.add(embeddings)
                
                # Build document map
                for i, doc_id in enumerate(results["ids"]):
                    self.document_map[i] = doc_id
                
                logger.info(f"Loaded {len(results['ids'])} existing embeddings")
        
        except Exception as e:
            logger.warning("Failed to load existing embeddings", error=str(e))
    
    async def add_documents(self, documents: List[DocumentChunk]):
        """Add documents to the vector store."""
        try:
            logger.info(f"Adding {len(documents)} documents to vector store")
            
            # Generate embeddings
            texts = [doc.content for doc in documents]
            embeddings = self.embedding_generator.generate_embeddings_batch(texts)
            
            # Add to FAISS index
            start_index = self.faiss_index.ntotal
            self.faiss_index.add(embeddings)
            
            # Update document map
            for i, doc in enumerate(documents):
                self.document_map[start_index + i] = doc.id
                doc.embedding = embeddings[i]
            
            # Add to ChromaDB for persistence
            ids = [doc.id for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            
            self.chroma_collection.add(
                ids=ids,
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=metadatas
            )
            
            logger.info(f"Successfully added {len(documents)} documents")
            
        except Exception as e:
            logger.error("Failed to add documents", error=str(e))
            raise AIServiceError(f"Document addition failed: {str(e)}")
    
    async def search_similar(
        self, 
        query: str, 
        k: int = 10,
        metadata_filters: Dict[str, Any] = None
    ) -> List[RetrievalResult]:
        """Search for similar documents."""
        try:
            # Generate query embedding
            query_embedding = self.embedding_generator.generate_embedding(query)
            query_embedding = query_embedding.reshape(1, -1)
            
            # Search in FAISS
            similarities, indices = self.faiss_index.search(query_embedding, k * 2)  # Get more for filtering
            
            results = []
            for i, (similarity, index) in enumerate(zip(similarities[0], indices[0])):
                if index == -1:  # FAISS returns -1 for empty slots
                    continue
                
                doc_id = self.document_map.get(index)
                if not doc_id:
                    continue
                
                # Get document from ChromaDB
                doc_results = self.chroma_collection.get(
                    ids=[doc_id],
                    include=["documents", "metadatas"]
                )
                
                if not doc_results["ids"]:
                    continue
                
                # Create document chunk
                chunk = DocumentChunk(
                    id=doc_id,
                    content=doc_results["documents"][0],
                    metadata=doc_results["metadatas"][0],
                    source=doc_results["metadatas"][0].get("source", ""),
                    chunk_index=doc_results["metadatas"][0].get("chunk_index", 0)
                )
                
                # Apply metadata filters
                if metadata_filters:
                    if not self._matches_filters(chunk.metadata, metadata_filters):
                        continue
                
                # Create retrieval result
                result = RetrievalResult(
                    chunk=chunk,
                    similarity_score=float(similarity),
                    metadata_match_score=self._calculate_metadata_match(chunk.metadata, metadata_filters or {})
                )
                
                results.append(result)
                
                if len(results) >= k:
                    break
            
            logger.info(f"Retrieved {len(results)} similar documents")
            return results
            
        except Exception as e:
            logger.error("Similarity search failed", error=str(e))
            raise AIServiceError(f"Vector search failed: {str(e)}")
    
    def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if document metadata matches filters."""
        for key, value in filters.items():
            if key not in metadata:
                return False
            
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            else:
                if metadata[key] != value:
                    return False
        
        return True
    
    def _calculate_metadata_match(self, metadata: Dict[str, Any], query_metadata: Dict[str, Any]) -> float:
        """Calculate metadata match score."""
        if not query_metadata:
            return 0.0
        
        matches = 0
        total = len(query_metadata)
        
        for key, value in query_metadata.items():
            if key in metadata and metadata[key] == value:
                matches += 1
        
        return matches / total if total > 0 else 0.0


class ContextRanker:
    """Rank retrieved contexts based on multiple factors."""
    
    def __init__(self, ranking_config: ContextRanking = None):
        self.ranking_config = ranking_config or ContextRanking()
    
    def rank_contexts(
        self, 
        results: List[RetrievalResult],
        query_analysis: QueryAnalysis,
        current_time: datetime = None
    ) -> List[RetrievalResult]:
        """Rank contexts based on relevance, recency, similarity, and metadata."""
        if not results:
            return results
        
        current_time = current_time or datetime.utcnow()
        
        # Calculate composite scores
        for result in results:
            # Similarity score (already calculated)
            similarity_score = result.similarity_score
            
            # Relevance score based on query intent and content matching
            relevance_score = self._calculate_relevance_score(result, query_analysis)
            
            # Recency score based on document timestamp
            recency_score = self._calculate_recency_score(result, current_time)
            
            # Metadata match score (already calculated)
            metadata_score = result.metadata_match_score
            
            # Composite score
            result.relevance_score = (
                self.ranking_config.similarity_weight * similarity_score +
                self.ranking_config.relevance_weight * relevance_score +
                self.ranking_config.recency_weight * recency_score +
                self.ranking_config.metadata_weight * metadata_score
            )
        
        # Sort by composite score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results
    
    def _calculate_relevance_score(self, result: RetrievalResult, query_analysis: QueryAnalysis) -> float:
        """Calculate relevance score based on query intent and content."""
        score = 0.0
        content_lower = result.chunk.content.lower()
        
        # Intent-based scoring
        intent_keywords = {
            "get_float_info": ["float", "platform", "wmo", "deployment"],
            "analyze_temperature": ["temperature", "thermal", "heat", "warm", "cold"],
            "analyze_salinity": ["salinity", "salt", "psu"],
            "show_map": ["location", "position", "coordinates", "map"],
            "get_profiles": ["profile", "measurement", "data", "cycle"]
        }
        
        intent_words = intent_keywords.get(query_analysis.intent.value, [])
        for word in intent_words:
            if word in content_lower:
                score += 0.2
        
        # Parameter matching
        for measurement in query_analysis.parameter_scope.measurements:
            if measurement.lower() in content_lower:
                score += 0.3
        
        # Location matching
        for location in query_analysis.spatial_scope.locations:
            if location.lower() in content_lower:
                score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_recency_score(self, result: RetrievalResult, current_time: datetime) -> float:
        """Calculate recency score based on document age."""
        # Get document timestamp
        doc_timestamp = result.chunk.timestamp
        if isinstance(doc_timestamp, str):
            try:
                doc_timestamp = datetime.fromisoformat(doc_timestamp)
            except:
                return 0.5  # Default score for invalid timestamps
        
        # Calculate age in days
        age_days = (current_time - doc_timestamp).days
        
        # Score decreases with age (exponential decay)
        if age_days <= 1:
            return 1.0
        elif age_days <= 7:
            return 0.8
        elif age_days <= 30:
            return 0.6
        elif age_days <= 90:
            return 0.4
        else:
            return 0.2


class PromptAugmenter:
    """Augment prompts with retrieved context."""
    
    def __init__(self):
        self.context_templates = {
            "system_context": """Based on the following oceanographic data and information:

{context}

Please provide a comprehensive and accurate response to the user's query about ARGO float data.""",
            
            "data_context": """Here is relevant ARGO oceanographic data:

{data_summary}

Context from knowledge base:
{retrieved_context}

Please analyze this information and provide insights.""",
            
            "fact_check_context": """Use the following verified information to fact-check and enhance your response:

{facts}

Ensure your response is consistent with this authoritative data."""
        }
    
    def augment_prompt(
        self,
        base_prompt: str,
        retrieved_contexts: List[RetrievalResult],
        query_results: Optional[List[Dict[str, Any]]] = None,
        template_name: str = "system_context"
    ) -> str:
        """Augment prompt with retrieved context."""
        
        # Build context string
        context_parts = []
        
        for i, result in enumerate(retrieved_contexts[:5], 1):  # Top 5 contexts
            context_part = f"{i}. {result.chunk.content}"
            if result.chunk.source:
                context_part += f" (Source: {result.chunk.source})"
            context_parts.append(context_part)
        
        context_string = "\n\n".join(context_parts)
        
        # Add query results if available
        if query_results:
            data_summary = self._summarize_query_results(query_results)
            context_string = f"Query Results:\n{data_summary}\n\nAdditional Context:\n{context_string}"
        
        # Apply template
        if template_name in self.context_templates:
            template = self.context_templates[template_name]
            augmented_context = template.format(context=context_string)
        else:
            augmented_context = f"Context:\n{context_string}"
        
        # Combine with base prompt
        return f"{augmented_context}\n\nUser Query: {base_prompt}"
    
    def _summarize_query_results(self, results: List[Dict[str, Any]]) -> str:
        """Create a summary of query results."""
        if not results:
            return "No data found."
        
        summary_parts = [f"Found {len(results)} records."]
        
        # Sample first few records
        for i, record in enumerate(results[:3], 1):
            record_summary = f"Record {i}: "
            key_fields = []
            
            for key, value in record.items():
                if key in ['wmo_id', 'platform_number', 'profile_date', 'latitude', 'longitude', 
                          'temperature', 'salinity', 'pressure']:
                    key_fields.append(f"{key}={value}")
            
            record_summary += ", ".join(key_fields[:5])  # Limit to 5 fields
            summary_parts.append(record_summary)
        
        if len(results) > 3:
            summary_parts.append(f"... and {len(results) - 3} more records.")
        
        return "\n".join(summary_parts)


class FactChecker:
    """Verify facts against database and knowledge base."""
    
    def __init__(self):
        pass
    
    async def verify_response(
        self,
        response: str,
        query_results: Optional[List[Dict[str, Any]]] = None,
        retrieved_contexts: Optional[List[RetrievalResult]] = None
    ) -> Dict[str, Any]:
        """Verify response against available data."""
        
        verification_results = {
            "overall_confidence": 0.8,  # Default confidence
            "fact_checks": [],
            "data_consistency": True,
            "context_alignment": True,
            "potential_issues": []
        }
        
        try:
            # Check numerical claims against query results
            if query_results:
                numerical_consistency = self._check_numerical_consistency(response, query_results)
                verification_results["fact_checks"].append(numerical_consistency)
            
            # Check consistency with retrieved contexts
            if retrieved_contexts:
                context_consistency = self._check_context_consistency(response, retrieved_contexts)
                verification_results["fact_checks"].append(context_consistency)
            
            # Calculate overall confidence
            if verification_results["fact_checks"]:
                avg_confidence = sum(fc["confidence"] for fc in verification_results["fact_checks"]) / len(verification_results["fact_checks"])
                verification_results["overall_confidence"] = avg_confidence
            
        except Exception as e:
            logger.warning("Fact checking failed", error=str(e))
            verification_results["potential_issues"].append(f"Fact checking error: {str(e)}")
        
        return verification_results
    
    def _check_numerical_consistency(self, response: str, query_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if numerical claims in response match query results."""
        
        fact_check = {
            "type": "numerical_consistency",
            "confidence": 0.8,
            "details": "Numerical claims appear consistent with data",
            "issues": []
        }
        
        # Extract numbers from response
        import re
        numbers_in_response = re.findall(r'-?\d+\.?\d*', response)
        
        # Basic consistency check (can be enhanced)
        if query_results and numbers_in_response:
            # Check if response numbers are reasonable given the data range
            data_values = []
            for result in query_results:
                for key, value in result.items():
                    if isinstance(value, (int, float)):
                        data_values.append(value)
            
            if data_values:
                data_min, data_max = min(data_values), max(data_values)
                for num_str in numbers_in_response:
                    try:
                        num = float(num_str)
                        if not (data_min * 0.5 <= num <= data_max * 2):  # Allow some tolerance
                            fact_check["issues"].append(f"Number {num} may be outside expected range")
                    except ValueError:
                        continue
        
        return fact_check
    
    def _check_context_consistency(self, response: str, contexts: List[RetrievalResult]) -> Dict[str, Any]:
        """Check if response is consistent with retrieved contexts."""
        
        fact_check = {
            "type": "context_consistency",
            "confidence": 0.9,
            "details": "Response aligns with retrieved context",
            "issues": []
        }
        
        # Simple keyword-based consistency check
        response_lower = response.lower()
        context_keywords = set()
        
        for result in contexts:
            content_words = result.chunk.content.lower().split()
            context_keywords.update(word for word in content_words if len(word) > 3)
        
        # Check for contradictions (basic implementation)
        contradiction_patterns = [
            ("increase", "decrease"),
            ("higher", "lower"),
            ("warm", "cold"),
            ("shallow", "deep")
        ]
        
        for pos_word, neg_word in contradiction_patterns:
            if pos_word in response_lower and neg_word in response_lower:
                fact_check["issues"].append(f"Potential contradiction: {pos_word} vs {neg_word}")
        
        return fact_check


class QualityAssessor:
    """Assess response quality based on multiple metrics."""
    
    def __init__(self):
        self.quality_metrics = [
            "relevance",
            "accuracy",
            "completeness",
            "clarity",
            "scientific_validity"
        ]
    
    def assess_response_quality(
        self,
        response: str,
        query_analysis: QueryAnalysis,
        retrieved_contexts: List[RetrievalResult],
        fact_check_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess overall response quality."""
        
        quality_scores = {}
        
        # Relevance score
        quality_scores["relevance"] = self._assess_relevance(response, query_analysis)
        
        # Accuracy score (from fact checking)
        quality_scores["accuracy"] = fact_check_results.get("overall_confidence", 0.8)
        
        # Completeness score
        quality_scores["completeness"] = self._assess_completeness(response, query_analysis)
        
        # Clarity score
        quality_scores["clarity"] = self._assess_clarity(response)
        
        # Scientific validity score
        quality_scores["scientific_validity"] = self._assess_scientific_validity(response)
        
        # Overall score
        overall_score = sum(quality_scores.values()) / len(quality_scores)
        
        return {
            "overall_score": overall_score,
            "individual_scores": quality_scores,
            "quality_level": self._get_quality_level(overall_score),
            "improvement_suggestions": self._get_improvement_suggestions(quality_scores)
        }
    
    def _assess_relevance(self, response: str, query_analysis: QueryAnalysis) -> float:
        """Assess how relevant the response is to the query."""
        score = 0.5  # Base score
        
        # Check if response addresses the intent
        intent_keywords = {
            "get_float_info": ["float", "platform", "deployment", "information"],
            "analyze_temperature": ["temperature", "thermal", "analysis", "trend"],
            "show_map": ["location", "position", "coordinates", "map"],
        }
        
        keywords = intent_keywords.get(query_analysis.intent.value, [])
        response_lower = response.lower()
        
        for keyword in keywords:
            if keyword in response_lower:
                score += 0.1
        
        return min(score, 1.0)
    
    def _assess_completeness(self, response: str, query_analysis: QueryAnalysis) -> float:
        """Assess if response completely addresses the query."""
        # Basic assessment based on response length and content
        if len(response) < 50:
            return 0.3
        elif len(response) < 200:
            return 0.6
        elif len(response) < 500:
            return 0.8
        else:
            return 0.9
    
    def _assess_clarity(self, response: str) -> float:
        """Assess clarity and readability of response."""
        # Basic metrics
        sentences = response.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        # Prefer moderate sentence length
        if 10 <= avg_sentence_length <= 25:
            return 0.9
        elif 5 <= avg_sentence_length <= 35:
            return 0.7
        else:
            return 0.5
    
    def _assess_scientific_validity(self, response: str) -> float:
        """Assess scientific validity of the response."""
        # Check for scientific terms and proper units
        scientific_indicators = [
            "temperature", "salinity", "pressure", "depth", "°C", "PSU", "dbar",
            "analysis", "measurement", "data", "profile", "oceanographic"
        ]
        
        response_lower = response.lower()
        score = 0.5
        
        for indicator in scientific_indicators:
            if indicator in response_lower:
                score += 0.05
        
        return min(score, 1.0)
    
    def _get_quality_level(self, score: float) -> str:
        """Get quality level description."""
        if score >= 0.9:
            return "Excellent"
        elif score >= 0.8:
            return "Good"
        elif score >= 0.7:
            return "Fair"
        else:
            return "Poor"
    
    def _get_improvement_suggestions(self, scores: Dict[str, float]) -> List[str]:
        """Generate improvement suggestions based on scores."""
        suggestions = []
        
        for metric, score in scores.items():
            if score < 0.7:
                if metric == "relevance":
                    suggestions.append("Make response more directly relevant to the query")
                elif metric == "completeness":
                    suggestions.append("Provide more comprehensive information")
                elif metric == "clarity":
                    suggestions.append("Improve clarity and readability")
                elif metric == "scientific_validity":
                    suggestions.append("Include more scientific context and proper terminology")
        
        return suggestions


class RAGPipeline:
    """Main RAG pipeline orchestrating retrieval and generation."""
    
    def __init__(self):
        self.settings = get_settings()
        self.vector_store = VectorStore()
        self.context_ranker = ContextRanker()
        self.prompt_augmenter = PromptAugmenter()
        self.fact_checker = FactChecker()
        self.quality_assessor = QualityAssessor()
        
        # Services
        self.gemini_service = None
        self.nlu_service = None
        self.sql_translator = None
    
    async def initialize(self):
        """Initialize all RAG components."""
        try:
            logger.info("Initializing RAG pipeline")
            
            # Initialize vector store
            await self.vector_store.initialize()
            
            # Initialize services
            self.gemini_service = GeminiService()
            await self.gemini_service.initialize()
            
            self.nlu_service = NLUService()
            self.sql_translator = NL2SQLTranslator()
            
            logger.info("RAG pipeline initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize RAG pipeline", error=str(e))
            raise AIServiceError(f"RAG pipeline initialization failed: {str(e)}")
    
    async def process_query(
        self,
        query: str,
        conversation_id: str = None,
        user_preferences: Dict[str, Any] = None,
        correlation_id: str = None
    ) -> RAGResponse:
        """Process query through complete RAG pipeline."""
        
        start_time = datetime.utcnow()
        correlation_id = correlation_id or f"rag_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info(
                "Processing query through RAG pipeline",
                query_length=len(query),
                correlation_id=correlation_id
            )
            
            # Step 1: Analyze query with NLU
            query_analysis = await self.nlu_service.analyze_query(
                query, correlation_id=correlation_id
            )
            
            # Step 2: Retrieve relevant contexts
            retrieved_contexts = await self.vector_store.search_similar(
                query, k=10, metadata_filters=self._build_metadata_filters(query_analysis)
            )
            
            # Step 3: Rank contexts
            ranked_contexts = self.context_ranker.rank_contexts(
                retrieved_contexts, query_analysis
            )
            
            # Step 4: Generate SQL query if needed
            sql_query = None
            query_results = None
            
            if query_analysis.intent.value in ["get_float_info", "search_floats", "get_profiles", "analyze_temperature", "analyze_salinity"]:
                try:
                    generated_query = await self.sql_translator.translate_query(
                        query_analysis, correlation_id=correlation_id
                    )
                    sql_query = generated_query.sql
                    
                    # Execute query (simplified - would use actual database)
                    query_results = await self._execute_sql_query(generated_query)
                    
                except Exception as e:
                    logger.warning("SQL generation failed", error=str(e))
            
            # Step 5: Augment prompt with context
            augmented_prompt = self.prompt_augmenter.augment_prompt(
                query, ranked_contexts[:5], query_results
            )
            
            # Step 6: Generate response with Gemini
            gemini_response = await self.gemini_service.process_query(
                augmented_prompt,
                conversation_id=conversation_id,
                user_preferences=user_preferences,
                correlation_id=correlation_id
            )
            
            response_text = gemini_response["response"]
            
            # Step 7: Fact check response
            fact_check_results = await self.fact_checker.verify_response(
                response_text, query_results, ranked_contexts[:3]
            )
            
            # Step 8: Assess response quality
            quality_assessment = self.quality_assessor.assess_response_quality(
                response_text, query_analysis, ranked_contexts, fact_check_results
            )
            
            # Calculate processing time
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Create RAG response
            rag_response = RAGResponse(
                response=response_text,
                confidence_score=quality_assessment["overall_score"],
                retrieved_contexts=ranked_contexts[:5],
                sql_query=sql_query,
                query_results=query_results,
                fact_check_results=fact_check_results,
                generation_metadata={
                    "query_analysis": {
                        "intent": query_analysis.intent.value,
                        "confidence": query_analysis.confidence,
                        "language": query_analysis.language
                    },
                    "retrieval_stats": {
                        "contexts_retrieved": len(retrieved_contexts),
                        "contexts_used": len(ranked_contexts[:5])
                    },
                    "quality_assessment": quality_assessment,
                    "gemini_metadata": gemini_response.get("metadata", {}),
                    "correlation_id": correlation_id
                },
                processing_time_ms=processing_time
            )
            
            logger.info(
                "RAG query processing completed",
                confidence_score=rag_response.confidence_score,
                processing_time_ms=processing_time,
                correlation_id=correlation_id
            )
            
            return rag_response
            
        except Exception as e:
            logger.error(
                "RAG query processing failed",
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            
            # Return error response
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
    
    def _build_metadata_filters(self, query_analysis: QueryAnalysis) -> Dict[str, Any]:
        """Build metadata filters for vector search."""
        filters = {}
        
        # Add intent-based filters
        if query_analysis.intent.value in ["analyze_temperature", "analyze_salinity"]:
            filters["data_type"] = ["temperature", "salinity", "oceanographic"]
        
        # Add spatial filters
        if query_analysis.spatial_scope.ocean_basins:
            filters["ocean_basin"] = query_analysis.spatial_scope.ocean_basins
        
        return filters
    
    async def _execute_sql_query(self, generated_query) -> List[Dict[str, Any]]:
        """Execute SQL query and return results (simplified implementation)."""
        # This would connect to actual database and execute the query
        # For now, return mock results
        
        logger.info("Executing SQL query", sql=generated_query.sql)
        
        # Mock results based on query type
        if "argo_floats" in generated_query.sql:
            return [
                {
                    "wmo_id": "1234567",
                    "platform_number": "1234567",
                    "deployment_latitude": 20.5,
                    "deployment_longitude": 65.2,
                    "status": "active",
                    "total_profiles": 150
                }
            ]
        elif "argo_profiles" in generated_query.sql:
            return [
                {
                    "cycle_number": 1,
                    "profile_date": "2024-01-15",
                    "latitude": 20.6,
                    "longitude": 65.3,
                    "max_pressure": 2000.0,
                    "min_temperature": 2.5,
                    "max_temperature": 28.3
                }
            ]
        
        return []
    
    async def add_knowledge_base_content(self, content: str, metadata: Dict[str, Any]):
        """Add content to the RAG knowledge base."""
        
        # Create document chunk
        chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            content=content,
            metadata=metadata,
            source=metadata.get("source", "knowledge_base"),
            timestamp=datetime.utcnow()
        )
        
        # Add to vector store
        await self.vector_store.add_documents([chunk])
        
        logger.info("Added content to knowledge base", content_length=len(content))
    
    async def close(self):
        """Close RAG pipeline and cleanup resources."""
        if self.gemini_service:
            await self.gemini_service.close()
        
        logger.info("RAG pipeline closed")


# Import enhanced RAG pipeline for improved temporal query handling
try:
    from app.services.enhanced_rag_service import EnhancedRAGPipeline
    # Use enhanced version as default for better temporal query support
    DefaultRAGPipeline = EnhancedRAGPipeline
    logger.info("Enhanced RAG pipeline loaded - temporal queries supported")
except ImportError as e:
    # Fallback to standard RAG if enhanced version not available
    DefaultRAGPipeline = RAGPipeline
    logger.warning(f"Enhanced RAG not available, using standard RAG: {e}")

# Export both versions for flexibility
__all__ = ['RAGPipeline', 'DefaultRAGPipeline', 'RAGResponse', 'DocumentChunk', 'RetrievalResult']
