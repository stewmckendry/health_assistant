#!/usr/bin/env python
"""
Check all possible ChromaDB locations and collections
"""

import chromadb
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

def check_all_collections():
    """Check all ChromaDB collections in all possible locations"""
    
    print("=" * 60)
    print("COMPREHENSIVE VECTOR STORE CHECK")
    print("=" * 60)
    
    # All possible paths for ChromaDB
    paths_to_check = [
        "data/processed/dr_off/chroma",
        ".chroma",
        "chroma",
        "data/chroma",
        "data/processed/chroma"
    ]
    
    all_collections = {}
    
    for path in paths_to_check:
        if os.path.exists(path):
            print(f"\n📁 Checking: {path}")
            
            try:
                client = chromadb.PersistentClient(path=path)
                collections = client.list_collections()
                
                if collections:
                    print(f"  ✅ Found {len(collections)} collection(s):")
                    for collection in collections:
                        count = collection.count()
                        print(f"    - {collection.name}: {count} documents")
                        all_collections[collection.name] = {
                            "path": path,
                            "count": count
                        }
                else:
                    print(f"  ⚠️ No collections in this location")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
        else:
            print(f"❌ Not found: {path}")
    
    print("\n" + "=" * 60)
    print("SUMMARY OF ALL COLLECTIONS FOUND:")
    print("=" * 60)
    
    if all_collections:
        for name, info in all_collections.items():
            print(f"  {name}:")
            print(f"    Location: {info['path']}")
            print(f"    Documents: {info['count']}")
    else:
        print("  No collections found!")
    
    print("\n" + "=" * 60)
    print("EXPECTED vs ACTUAL:")
    print("=" * 60)
    
    expected = {
        "ohip_documents": "OHIP Schedule chunks",
        "adp_documents": "ADP manual chunks",
        "odb_documents": "ODB formulary chunks",
        "ohip_chunks": "OHIP Act chunks",
        "adp_v1": "ADP embeddings"
    }
    
    for exp_name, description in expected.items():
        if exp_name in all_collections:
            print(f"  ✅ {exp_name}: Found ({description})")
        else:
            print(f"  ❌ {exp_name}: Missing ({description})")

if __name__ == "__main__":
    check_all_collections()