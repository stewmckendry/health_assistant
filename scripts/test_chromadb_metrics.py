#!/usr/bin/env python3
"""
Test ChromaDB metrics and fix similarity calculation
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import chromadb
from chromadb.config import Settings
import openai
import numpy as np

def test_metrics():
    """Test different distance metrics in ChromaDB"""
    
    print("🔍 Testing ChromaDB Distance Metrics...")
    chroma_path = 'data/dr_off_agent/processed/dr_off/chroma'
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
    
    # Get current collection info
    try:
        collection = client.get_collection('ohip_documents')
        print(f"✅ Current collection exists with {collection.count()} documents")
        print(f"📊 Collection metadata: {collection.metadata}")
        
        # Check what distance function is being used
        # ChromaDB default is L2 (euclidean)
        
    except Exception as e:
        print(f"❌ Error getting collection: {e}")
        return
    
    # Test creating a new collection with cosine similarity
    print("\n🧪 Testing new collection with cosine similarity...")
    
    try:
        # Delete test collection if it exists
        try:
            client.delete_collection('ohip_documents_cosine')
        except:
            pass
            
        # Create new collection with cosine similarity
        test_collection = client.create_collection(
            name='ohip_documents_cosine',
            metadata={
                "hnsw:space": "cosine",  # Use cosine similarity instead of L2
                "source": "ohip"
            }
        )
        print("✅ Created test collection with cosine similarity")
        
        # Get a few documents from original collection
        sample_docs = collection.get(
            where={"fee_code": "C122"},
            include=["documents", "embeddings", "metadatas"],
            limit=1
        )
        
        if sample_docs['documents']:
            # Add to test collection
            test_collection.add(
                ids=["test_c122"],
                embeddings=sample_docs['embeddings'],
                documents=sample_docs['documents'],
                metadatas=sample_docs['metadatas']
            )
            print(f"✅ Added C122 document to test collection")
            
            # Test query with OpenAI embedding
            openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            query = "hospital admission assessment"
            query_embedding = openai_client.embeddings.create(
                input=[query],
                model="text-embedding-3-small"
            ).data[0].embedding
            
            # Query original collection (L2)
            l2_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=1,
                where={"fee_code": "C122"}
            )
            
            # Query test collection (cosine)
            cosine_results = test_collection.query(
                query_embeddings=[query_embedding],
                n_results=1
            )
            
            print(f"\n📊 Results Comparison:")
            print(f"Query: '{query}'")
            print(f"Document: C122 - {sample_docs['documents'][0][:80]}...")
            
            if l2_results['distances'][0]:
                l2_distance = l2_results['distances'][0][0]
                print(f"\nL2 (original) distance: {l2_distance:.4f}")
                print(f"L2 similarity (1 - distance): {1 - l2_distance:.4f}")
            
            if cosine_results['distances'][0]:
                cosine_distance = cosine_results['distances'][0][0]
                print(f"\nCosine distance: {cosine_distance:.4f}")
                print(f"Cosine similarity (1 - distance): {1 - cosine_distance:.4f}")
            
            # Calculate actual cosine similarity manually
            doc_embedding = np.array(sample_docs['embeddings'][0])
            query_emb_np = np.array(query_embedding)
            
            # Normalize vectors
            doc_norm = doc_embedding / np.linalg.norm(doc_embedding)
            query_norm = query_emb_np / np.linalg.norm(query_emb_np)
            
            manual_cosine = np.dot(doc_norm, query_norm)
            print(f"\n✅ Manual cosine similarity: {manual_cosine:.4f}")
            
            # Check if embeddings are normalized
            doc_magnitude = np.linalg.norm(doc_embedding)
            query_magnitude = np.linalg.norm(query_emb_np)
            print(f"\n🔍 Embedding magnitudes:")
            print(f"Document embedding magnitude: {doc_magnitude:.4f}")
            print(f"Query embedding magnitude: {query_magnitude:.4f}")
            print(f"Are embeddings normalized? {abs(doc_magnitude - 1.0) < 0.01 and abs(query_magnitude - 1.0) < 0.01}")
            
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_metrics()