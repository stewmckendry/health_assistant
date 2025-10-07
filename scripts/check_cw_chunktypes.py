#!/usr/bin/env python3
"""Check chunk_type values in Choosing Wisely collection."""
import chromadb

client = chromadb.PersistentClient(path="data/dr_opa_agent/chroma")
collection = client.get_collection(name="opa_choosing_wisely_corpus")

# Get all items
results = collection.get(limit=50, include=['metadatas'])

# Collect unique chunk_type values
chunk_types = {}
for metadata in results['metadatas']:
    ct = metadata.get('chunk_type', 'MISSING')
    dt = metadata.get('doc_type', 'MISSING')
    key = f"chunk_type={ct}, doc_type={dt}"
    chunk_types[key] = chunk_types.get(key, 0) + 1

print("\nChoosing Wisely Collection - chunk_type and doc_type values:")
print("="*80)
for key, count in sorted(chunk_types.items(), key=lambda x: -x[1]):
    print(f"  {key}: {count} chunks")
