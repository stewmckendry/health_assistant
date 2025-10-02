#!/usr/bin/env python3
"""
Check metadata in quality standards collection
"""

import chromadb
from chromadb.config import Settings
from pathlib import Path

# Initialize local Chroma client
chroma_path = "data/dr_opa_agent/chroma"
chroma_client = chromadb.PersistentClient(
    path=chroma_path,
    settings=Settings(anonymized_telemetry=False)
)

# Get the quality standards collection
try:
    collection = chroma_client.get_collection("opa_quality_standards_corpus")
    
    # Get a sample of documents
    results = collection.get(
        limit=10,
        include=['metadatas', 'documents']
    )
    
    print("=" * 80)
    print("QUALITY STANDARDS COLLECTION METADATA")
    print("=" * 80)
    print(f"\nTotal documents in collection: {collection.count()}")
    print("\nSample metadata from first 10 documents:")
    print("-" * 40)
    
    # Collect unique values for key fields
    sources = set()
    doc_types = set()
    chunk_types = set()
    titles = set()
    
    for i, metadata in enumerate(results['metadatas'], 1):
        print(f"\nDocument {i}:")
        print(f"  ID: {results['ids'][i-1]}")
        print(f"  Title: {metadata.get('title', 'N/A')}")
        print(f"  Source: {metadata.get('source', 'N/A')}")
        print(f"  Doc Type: {metadata.get('doc_type', 'N/A')}")
        print(f"  Chunk Type: {metadata.get('chunk_type', 'N/A')}")
        print(f"  Text preview: {results['documents'][i-1][:100]}...")
        
        # Collect unique values
        if 'source' in metadata:
            sources.add(metadata['source'])
        if 'doc_type' in metadata:
            doc_types.add(metadata['doc_type'])
        if 'chunk_type' in metadata:
            chunk_types.add(metadata['chunk_type'])
        if 'title' in metadata:
            titles.add(metadata['title'])
    
    # Get ALL metadata to analyze patterns
    all_results = collection.get(
        include=['metadatas']
    )
    
    # Analyze all metadata
    all_sources = set()
    all_doc_types = set()
    all_chunk_types = set()
    all_titles = set()
    
    for metadata in all_results['metadatas']:
        if 'source' in metadata:
            all_sources.add(metadata['source'])
        if 'doc_type' in metadata:
            all_doc_types.add(metadata['doc_type'])
        if 'chunk_type' in metadata:
            all_chunk_types.add(metadata['chunk_type'])
        if 'title' in metadata:
            all_titles.add(metadata['title'])
    
    print("\n" + "=" * 80)
    print("METADATA VALUE ANALYSIS")
    print("=" * 80)
    
    print(f"\nUnique 'source' values ({len(all_sources)}):")
    for source in sorted(all_sources):
        print(f"  - {source}")
    
    print(f"\nUnique 'doc_type' values ({len(all_doc_types)}):")
    for doc_type in sorted(all_doc_types):
        print(f"  - {doc_type}")
    
    print(f"\nUnique 'chunk_type' values ({len(all_chunk_types)}):")
    for chunk_type in sorted(all_chunk_types):
        print(f"  - {chunk_type}")
    
    print(f"\nUnique quality standards ({len(all_titles)}):")
    for title in sorted(all_titles)[:10]:  # Show first 10
        print(f"  - {title}")
    if len(all_titles) > 10:
        print(f"  ... and {len(all_titles) - 10} more")
    
    # Count by doc_type
    doc_type_counts = {}
    for metadata in all_results['metadatas']:
        dt = metadata.get('doc_type', 'unknown')
        doc_type_counts[dt] = doc_type_counts.get(dt, 0) + 1
    
    print(f"\nDocument counts by doc_type:")
    for doc_type, count in sorted(doc_type_counts.items()):
        print(f"  {doc_type}: {count}")
    
except Exception as e:
    print(f"Error: {e}")