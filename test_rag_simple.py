#!/usr/bin/env python3
"""
Simple test of RAG pipeline with existing vector data.
"""

import asyncio
import chromadb
from sentence_transformers import SentenceTransformer
import sys
from pathlib import Path

# Add app to Python path
sys.path.append(str(Path(__file__).parent))

from app.services.real_gemini_service import real_gemini_service

async def test_simple_rag():
    """Test simple RAG workflow with existing data."""
    
    print("🧠 Testing Simple RAG Pipeline")
    print("=" * 40)
    
    # 1. Initialize ChromaDB
    print("1. Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path='./data/chromadb')
    collections = client.list_collections()
    
    if not collections:
        print("❌ No collections found in ChromaDB")
        return
    
    collection = collections[0]  # Use first collection
    print(f"✅ Found collection: {collection.name} with {collection.count()} documents")
    
    # 2. Initialize embedding model
    print("2. Loading embedding model...")
    try:
        embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        print("✅ Embedding model loaded")
    except Exception as e:
        print(f"❌ Failed to load embedding model: {e}")
        return
    
    # 3. Test query
    query = "Show me ocean temperature data near India from ARGO floats"
    print(f"3. Processing query: '{query}'")
    
    # Generate query embedding
    query_embedding = embedder.encode([query])
    
    # Search vector database
    print("4. Searching vector database...")
    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=5,
        include=['documents', 'metadatas', 'distances']
    )
    
    print(f"✅ Found {len(results['documents'][0])} relevant documents")
    
    # 5. Build context
    contexts = []
    for i, doc in enumerate(results['documents'][0]):
        metadata = results['metadatas'][0][i]
        distance = results['distances'][0][i]
        contexts.append(f"Context {i+1} (similarity: {1-distance:.3f}): {doc[:200]}...")
        print(f"   • {doc[:100]}... (similarity: {1-distance:.3f})")
    
    # 6. Generate response with Gemini
    print("5. Generating AI response...")
    
    context_text = "\n\n".join(contexts)
    enhanced_prompt = f"""You are FloatChat, an expert in ARGO oceanographic data. Based on the following relevant information from our ARGO database, answer the user's query:

RELEVANT DATA:
{context_text}

USER QUERY: {query}

Provide a comprehensive response based on the retrieved data above. Reference specific data points, locations, and measurements when available."""

    try:
        response = await real_gemini_service._generate_response(enhanced_prompt)
        print(f"✅ Generated response ({len(response)} characters)")
        print(f"\n📝 RESPONSE:\n{response[:500]}...")
        
        return {
            "query": query,
            "contexts_found": len(results['documents'][0]),
            "response": response,
            "rag_working": True
        }
        
    except Exception as e:
        print(f"❌ Failed to generate response: {e}")
        return None

if __name__ == "__main__":
    result = asyncio.run(test_simple_rag())
    if result:
        print("\n🎉 Simple RAG test successful!")
    else:
        print("\n❌ Simple RAG test failed!")
