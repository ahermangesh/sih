#!/usr/bin/env python3
"""
FloatChat RAG System Optimization

Optimize the RAG pipeline for better performance according to 
Professional Development Plan targets:
- Response Time: <3 seconds (currently ~10s)
- Query Accuracy: >90% 
- Context Retrieval: Improved relevance
"""

import time
import asyncio
from sentence_transformers import SentenceTransformer
import chromadb
import numpy as np
from typing import List, Dict, Any
import json
import sys
from pathlib import Path

# Add app to Python path
sys.path.append(str(Path(__file__).parent))

class OptimizedRAGService:
    """Optimized RAG service with caching and performance improvements."""
    
    def __init__(self):
        self.embedder = None
        self.chroma_client = None
        self.collection = None
        self.embedding_cache = {}  # Cache for query embeddings
        self.context_cache = {}    # Cache for retrieved contexts
        self.initialized = False
    
    async def initialize(self):
        """Initialize with optimizations."""
        if self.initialized:
            return
            
        print("🚀 Initializing Optimized RAG Service...")
        
        start_time = time.time()
        
        # Load embedding model with optimizations
        print("   Loading embedding model...")
        self.embedder = SentenceTransformer(
            'sentence-transformers/all-MiniLM-L6-v2',
            device='cpu'  # Ensure CPU usage for consistency
        )
        
        # Connect to ChromaDB
        print("   Connecting to ChromaDB...")
        self.chroma_client = chromadb.PersistentClient(path='./data/chromadb')
        collections = self.chroma_client.list_collections()
        
        if collections:
            self.collection = collections[0]
            print(f"   Connected to collection: {self.collection.name} ({self.collection.count()} documents)")
        else:
            raise Exception("No ChromaDB collections found")
        
        init_time = time.time() - start_time
        print(f"✅ RAG Service initialized in {init_time:.2f}s")
        
        self.initialized = True
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for query."""
        return f"query_{hash(query.lower().strip())}"
    
    async def search_contexts(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Optimized context search with caching."""
        
        cache_key = self._get_cache_key(query)
        
        # Check cache first
        if cache_key in self.context_cache:
            print(f"   📦 Using cached results for query")
            return self.context_cache[cache_key]
        
        start_time = time.time()
        
        # Generate embedding
        if cache_key in self.embedding_cache:
            query_embedding = self.embedding_cache[cache_key]
        else:
            query_embedding = self.embedder.encode([query])
            self.embedding_cache[cache_key] = query_embedding
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Process and rank results
        processed_results = self._process_search_results(results, query)
        
        # Cache results (with TTL simulation - in production use Redis with TTL)
        self.context_cache[cache_key] = processed_results
        
        # Limit cache size (simple LRU simulation)
        if len(self.context_cache) > 100:
            # Remove oldest entries
            oldest_keys = list(self.context_cache.keys())[:20]
            for key in oldest_keys:
                del self.context_cache[key]
        
        search_time = time.time() - start_time
        print(f"   🔍 Context search completed in {search_time:.2f}s")
        
        return processed_results
    
    def _process_search_results(self, results: Dict, query: str) -> Dict[str, Any]:
        """Process and enhance search results."""
        
        processed_contexts = []
        query_lower = query.lower()
        
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            similarity = 1 - distance
            
            # Enhanced relevance scoring
            relevance_score = self._calculate_relevance_score(doc, query_lower, similarity)
            
            context = {
                "content": doc,
                "metadata": metadata,
                "similarity": similarity,
                "relevance_score": relevance_score,
                "rank": i
            }
            
            processed_contexts.append(context)
        
        # Re-rank by relevance score
        processed_contexts.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return {
            "contexts": processed_contexts,
            "total_found": len(processed_contexts),
            "best_similarity": max(c['similarity'] for c in processed_contexts) if processed_contexts else 0
        }
    
    def _calculate_relevance_score(self, doc: str, query_lower: str, base_similarity: float) -> float:
        """Calculate enhanced relevance score."""
        
        doc_lower = doc.lower()
        score = base_similarity
        
        # Boost for exact keyword matches
        query_words = query_lower.split()
        for word in query_words:
            if len(word) > 3:  # Skip short words
                if word in doc_lower:
                    score += 0.1
        
        # Boost for important oceanographic terms
        important_terms = [
            'temperature', 'salinity', 'pressure', 'depth',
            'indian ocean', 'arabian sea', 'bay of bengal',
            'argo', 'float', 'profile', 'measurement'
        ]
        
        for term in important_terms:
            if term in query_lower and term in doc_lower:
                score += 0.15
        
        # Boost for recent data (if query mentions recent/latest)
        if any(word in query_lower for word in ['recent', 'latest', '2024', '2025']):
            if any(year in doc_lower for year in ['2024', '2025']):
                score += 0.2
        
        return min(score, 1.0)  # Cap at 1.0
    
    def build_enhanced_prompt(self, query: str, contexts: List[Dict], max_context_length: int = 2000) -> str:
        """Build optimized prompt with context."""
        
        # Select top contexts within length limit
        selected_contexts = []
        current_length = 0
        
        for context in contexts:
            content = context['content']
            if current_length + len(content) < max_context_length:
                selected_contexts.append(content)
                current_length += len(content)
            else:
                break
        
        context_text = "\n\n".join(selected_contexts)
        
        # Build enhanced prompt
        prompt = f"""You are FloatChat, an expert oceanographic data analyst specializing in ARGO float data. 

Based on the following relevant ARGO data from our database, provide a comprehensive and accurate response to the user's query.

RELEVANT ARGO DATA:
{context_text}

USER QUERY: {query}

INSTRUCTIONS:
- Reference specific ARGO float IDs, dates, locations, and measurements when available
- Provide quantitative data (temperatures, salinities, coordinates) with units
- Explain the oceanographic context and significance
- Be precise and scientific while remaining conversational
- If the data doesn't fully answer the query, clearly state the limitations

RESPONSE:"""

        return prompt


async def test_optimization():
    """Test the optimized RAG service."""
    
    print("🧪 Testing Optimized RAG Service")
    print("=" * 50)
    
    rag = OptimizedRAGService()
    await rag.initialize()
    
    # Test queries
    test_queries = [
        "Show me recent ocean temperature data from ARGO floats near India",
        "What is the salinity in the Arabian Sea?",
        "Find temperature measurements above 25°C in tropical regions"
    ]
    
    total_time = 0
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Test {i}: {query}")
        
        start_time = time.time()
        
        # Search contexts
        results = await rag.search_contexts(query)
        
        # Build prompt
        prompt = rag.build_enhanced_prompt(query, results['contexts'])
        
        query_time = time.time() - start_time
        total_time += query_time
        
        print(f"   ⏱️  Query Time: {query_time:.2f}s")
        print(f"   📊 Contexts Found: {results['total_found']}")
        print(f"   🎯 Best Similarity: {results['best_similarity']:.3f}")
        print(f"   📝 Prompt Length: {len(prompt)} characters")
        
        # Show top context
        if results['contexts']:
            top_context = results['contexts'][0]
            print(f"   🔝 Top Context: {top_context['content'][:100]}...")
            print(f"      Relevance Score: {top_context['relevance_score']:.3f}")
    
    avg_time = total_time / len(test_queries)
    print(f"\n📈 PERFORMANCE SUMMARY:")
    print(f"   Average Query Time: {avg_time:.2f}s")
    print(f"   Target: <3s total (including AI generation)")
    print(f"   Status: {'✅ ON TRACK' if avg_time < 2 else '⚠️ NEEDS MORE OPTIMIZATION'}")


if __name__ == "__main__":
    asyncio.run(test_optimization())
