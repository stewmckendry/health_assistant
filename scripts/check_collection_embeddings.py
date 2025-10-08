#!/usr/bin/env python3
"""Check the embedding configuration of Dr. OPA collections."""
import chromadb
import sys

# Check Dr. OPA collections
db_path = "data/dr_opa_agent/chroma"
client = chromadb.PersistentClient(path=db_path)

print(f"\nChecking ChromaDB at: {db_path}\n")
print("="*80)

collections = client.list_collections()
for collection in collections:
    name = collection.name
    if 'opa' in name.lower():
        print(f"\nCollection: {name}")
        print("-"*80)

        # Get collection metadata
        coll = client.get_collection(name=name)

        # Get first few items to check dimensions
        results = coll.get(limit=5, include=['embeddings', 'metadatas'])

        if results['embeddings'] is not None and len(results['embeddings']) > 0:
            first_embedding = results['embeddings'][0]
            print(f"  Embedding dimension: {len(first_embedding)}")
            print(f"  Total documents: {coll.count()}")

            # Check metadata structure
            if results['metadatas']:
                print(f"  Sample metadata keys: {list(results['metadatas'][0].keys())}")
                if 'document_type' in results['metadatas'][0]:
                    print(f"  Sample document_type: {results['metadatas'][0]['document_type']}")
                if 'doc_type' in results['metadatas'][0]:
                    print(f"  Sample doc_type: {results['metadatas'][0]['doc_type']}")
                if 'source' in results['metadatas'][0]:
                    print(f"  Sample source: {results['metadatas'][0]['source']}")
        else:
            print(f"  No embeddings found (collection may be empty)")

print("\n" + "="*80)
