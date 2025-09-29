#!/usr/bin/env python3
"""
Debug script to test ChromaDB storage directly
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import chromadb
from chromadb.config import Settings
from src.agents.dr_off_agent.ingestion.ingesters.ohip_ingester import EnhancedOHIPIngester
import os

def debug_chromadb():
    """Debug ChromaDB storage directly"""
    
    print("Debugging ChromaDB storage...")
    chroma_path = 'data/dr_off_agent/processed/dr_off/chroma'
    
    # Test 1: Check collection
    client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
    collections = client.list_collections()
    print(f"Existing collections: {[c.name for c in collections]}")
    
    # Test 2: Try to get collection
    try:
        collection = client.get_collection('ohip_documents')
        count = collection.count()
        print(f"ohip_documents collection exists with {count} documents")
    except Exception as e:
        print(f"Error getting collection: {e}")
        return
    
    # Test 3: Create ingester and test storage
    print("\nTesting ingester storage...")
    ingester = EnhancedOHIPIngester(
        chroma_path=chroma_path,
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    
    # Test 4: Generate embeddings and try to store manually
    test_texts = ["OHIP Fee Code C122 - Test document for vector storage"]
    embeddings = ingester.generate_embeddings(test_texts)
    print(f"Generated embedding: {len(embeddings[0])} dimensions, sum: {sum(embeddings[0]):.4f}")
    
    # Test 5: Try direct ChromaDB add
    try:
        test_id = "test_chunk_123"
        print(f"\nTrying to add document directly to ChromaDB...")
        
        # Check if document already exists
        try:
            existing = collection.get(ids=[test_id])
            if existing['ids']:
                print(f"Document {test_id} already exists, deleting...")
                collection.delete(ids=[test_id])
        except Exception as e:
            print(f"No existing document to delete: {e}")
        
        collection.add(
            ids=[test_id],
            embeddings=[embeddings[0]],
            documents=[test_texts[0]],
            metadatas=[{
                'source_type': 'ohip',
                'document_type': 'test',
                'fee_code': 'C122'
            }]
        )
        
        print(f"Successfully added test document!")
        
        # Verify it was added
        new_count = collection.count()
        print(f"Collection now has {new_count} documents")
        
        # Try to retrieve it
        result = collection.get(ids=[test_id])
        print(f"Retrieved document: {result['documents'][0][:100]}...")
        
    except Exception as e:
        print(f"Error adding to ChromaDB: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_chromadb()