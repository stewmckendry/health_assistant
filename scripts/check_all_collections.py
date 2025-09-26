#!/usr/bin/env python3
"""
Check all ChromaDB collections and their document counts
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

def check_all_collections():
    """Check all ChromaDB collections and their counts"""
    
    print("Checking all ChromaDB collections...")
    chroma_path = 'data/dr_off_agent/processed/dr_off/chroma'
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
    collections = client.list_collections()
    
    print(f"\nFound {len(collections)} collections:")
    print("-" * 50)
    
    for collection in collections:
        try:
            col = client.get_collection(collection.name)
            count = col.count()
            print(f"{collection.name:20} {count:,} documents")
            
            # Sample a few documents to see their structure
            if count > 0:
                sample = col.peek(limit=2)
                print(f"  Sample documents:")
                for i, doc in enumerate(sample['documents']):
                    print(f"    {i+1}: {doc[:100]}...")
                print()
                
        except Exception as e:
            print(f"{collection.name:20} Error: {e}")
    
    print("-" * 50)
    total_docs = sum([client.get_collection(c.name).count() for c in collections])
    print(f"Total documents across all collections: {total_docs:,}")

if __name__ == "__main__":
    check_all_collections()