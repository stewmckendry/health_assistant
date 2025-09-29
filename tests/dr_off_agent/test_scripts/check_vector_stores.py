#!/usr/bin/env python
"""
Check what vector store collections exist and their contents
"""

import chromadb
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

def check_collections():
    """Check all ChromaDB collections"""
    
    print("=" * 60)
    print("VECTOR STORE COLLECTIONS CHECK")
    print("=" * 60)
    
    # Possible paths for ChromaDB
    paths_to_check = [
        "data/processed/dr_off/chroma",
        ".chroma",
        "chroma",
        "data/chroma"
    ]
    
    for path in paths_to_check:
        if os.path.exists(path):
            print(f"\n📁 Found ChromaDB at: {path}")
            
            try:
                client = chromadb.PersistentClient(path=path)
                collections = client.list_collections()
                
                print(f"  Collections found: {len(collections)}")
                
                for collection in collections:
                    print(f"\n  Collection: {collection.name}")
                    count = collection.count()
                    print(f"    Documents: {count}")
                    
                    # Get sample metadata
                    if count > 0:
                        sample = collection.peek(1)
                        if sample['metadatas']:
                            print(f"    Sample metadata: {sample['metadatas'][0]}")
                        if sample['documents']:
                            print(f"    Sample text (50 chars): {sample['documents'][0][:50]}...")
                            
            except Exception as e:
                print(f"  ❌ Error reading ChromaDB: {e}")
        else:
            print(f"✗ Not found: {path}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    check_collections()