#!/usr/bin/env python3
"""
Test vector search directly in ChromaDB for C122
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

def test_vector_search():
    """Test vector search for C122 directly"""
    
    print("Testing vector search for C122...")
    chroma_path = 'data/dr_off_agent/processed/dr_off/chroma'
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
    collection = client.get_collection('ohip_documents')
    
    print(f"Collection has {collection.count()} documents")
    
    # Test 1: Search for "C122" directly in text
    print("\n=== Test 1: Direct text search for C122 ===")
    try:
        results = collection.get(
            where={"$and": [
                {"source_type": "ohip"},
                {"fee_code": "C122"}
            ]},
            include=["documents", "metadatas"]
        )
        
        if results['documents']:
            print(f"Found {len(results['documents'])} direct matches for C122:")
            for i, doc in enumerate(results['documents']):
                print(f"  {i+1}: {doc[:100]}...")
                print(f"      Metadata: {results['metadatas'][i]}")
        else:
            print("No direct matches found for C122 in metadata")
    except Exception as e:
        print(f"Direct search error: {e}")
    
    # Test 2: Text search for "C122" in document content
    print("\n=== Test 2: Text search in document content ===")
    try:
        all_results = collection.get(
            where={"source_type": "ohip"},
            include=["documents", "metadatas"]
        )
        
        c122_docs = []
        for i, doc in enumerate(all_results['documents']):
            if "C122" in doc:
                c122_docs.append((doc, all_results['metadatas'][i]))
        
        print(f"Found {len(c122_docs)} documents containing 'C122':")
        for doc, meta in c122_docs[:3]:  # Show first 3
            print(f"  Document: {doc[:150]}...")
            print(f"  Metadata: {meta}\n")
            
    except Exception as e:
        print(f"Content search error: {e}")
    
    # Test 3: Vector search for hospital admission
    print("\n=== Test 3: Vector search for 'hospital admission' ===")
    try:
        # Generate embedding for query
        openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        query_embedding = openai_client.embeddings.create(
            input=["hospital admission assessment"],
            model="text-embedding-3-small"
        ).data[0].embedding
        
        # Search in collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=10,
            where={"source_type": "ohip"}
        )
        
        print(f"Vector search returned {len(results['documents'][0])} results:")
        for i, doc in enumerate(results['documents'][0][:5]):
            distance = results['distances'][0][i]
            similarity = 1 - distance
            print(f"  {i+1} (similarity: {similarity:.3f}): {doc[:100]}...")
            
    except Exception as e:
        print(f"Vector search error: {e}")

if __name__ == "__main__":
    test_vector_search()