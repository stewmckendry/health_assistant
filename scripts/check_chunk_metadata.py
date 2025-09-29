#!/usr/bin/env python3
"""
Check if drug metadata is preserved across all chunks
"""

import chromadb
from collections import defaultdict

def check_chunk_metadata():
    """Verify metadata preservation in multi-chunk drugs"""
    
    print("🔍 Checking Chunk Metadata Preservation")
    print("=" * 60)
    
    # Connect to ChromaDB
    chroma_path = "data/dr_off_agent/processed/dr_off/chroma"
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection("odb_documents")
    
    # Get all drug chunks
    drug_chunks = collection.get(
        where={"source_type": "odb_drug"},
        limit=100,  # Sample size
        include=['documents', 'metadatas']
    )
    
    # Group chunks by DIN to see multi-chunk drugs
    chunks_by_din = defaultdict(list)
    for i, metadata in enumerate(drug_chunks['metadatas']):
        din = metadata.get('din', 'NO_DIN')
        chunk_data = {
            'id': drug_chunks['ids'][i],
            'metadata': metadata,
            'text_preview': drug_chunks['documents'][i][:200]
        }
        chunks_by_din[din].append(chunk_data)
    
    # Find drugs with multiple chunks
    multi_chunk_drugs = {din: chunks for din, chunks in chunks_by_din.items() if len(chunks) > 1}
    
    print(f"\n📊 Statistics:")
    print(f"  Total drug chunks sampled: {len(drug_chunks['ids'])}")
    print(f"  Unique DINs: {len(chunks_by_din)}")
    print(f"  Drugs with multiple chunks: {len(multi_chunk_drugs)}")
    
    if multi_chunk_drugs:
        # Show a multi-chunk example
        din, chunks = list(multi_chunk_drugs.items())[0]
        print(f"\n📝 Example Multi-Chunk Drug (DIN: {din}):")
        print(f"  Number of chunks: {len(chunks)}")
        
        for i, chunk in enumerate(chunks):
            print(f"\n  Chunk {i+1}:")
            print(f"    ID: {chunk['id'][:20]}...")
            print(f"    Metadata preserved:")
            print(f"      - DIN: {chunk['metadata'].get('din', 'MISSING')}")
            print(f"      - Generic: {chunk['metadata'].get('generic_name', 'MISSING')}")
            print(f"      - Brand: {chunk['metadata'].get('brand_name', 'MISSING')}")
            print(f"      - Therapeutic: {chunk['metadata'].get('therapeutic_class', 'MISSING')}")
            print(f"    Text starts with: {chunk['text_preview'][:100]}...")
    
    # Check for chunks without critical metadata
    print(f"\n⚠️  Checking for metadata issues:")
    missing_din = 0
    missing_generic = 0
    missing_brand = 0
    
    for metadata in drug_chunks['metadatas']:
        if not metadata.get('din'):
            missing_din += 1
        if not metadata.get('generic_name'):
            missing_generic += 1
        if not metadata.get('brand_name'):
            missing_brand += 1
    
    print(f"  Chunks missing DIN: {missing_din}")
    print(f"  Chunks missing generic_name: {missing_generic}")
    print(f"  Chunks missing brand_name: {missing_brand}")
    
    if missing_din > 0:
        print("\n  ❌ CONTEXT LOSS RISK: Some chunks are missing DIN metadata!")
    else:
        print("\n  ✅ All chunks have DIN metadata preserved")
    
    print("\n✨ Check complete!")

if __name__ == "__main__":
    check_chunk_metadata()