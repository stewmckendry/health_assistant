#!/usr/bin/env python3
"""
Test ODB drug embeddings in ChromaDB
"""

import chromadb
from pathlib import Path

def test_odb_embeddings():
    """Test that drug embeddings were created"""
    
    print("🔍 Testing ODB Drug Embeddings")
    print("=" * 60)
    
    # Connect to ChromaDB
    chroma_path = "data/dr_off_agent/processed/dr_off/chroma"
    client = chromadb.PersistentClient(path=chroma_path)
    
    try:
        collection = client.get_collection("odb_documents")
        
        # Get total count (ChromaDB doesn't have count, so we get all IDs)
        all_items = collection.get(
            limit=20000,  # High limit to get all
            include=['metadatas']
        )
        
        total_count = len(all_items['ids'])
        print(f"\n📊 Total documents in collection: {total_count:,}")
        
        # Count by source type
        source_types = {}
        for metadata in all_items['metadatas']:
            source_type = metadata.get('source_type', 'unknown')
            source_types[source_type] = source_types.get(source_type, 0) + 1
        
        print(f"\n📝 Documents by type:")
        for stype, count in source_types.items():
            print(f"  - {stype}: {count:,}")
        
        # Get sample drug embeddings
        print(f"\n💊 Sample Drug Embeddings:")
        drug_samples = collection.get(
            where={"source_type": "odb_drug"},
            limit=5,
            include=['documents', 'metadatas']
        )
        
        if drug_samples['ids']:
            for i in range(min(5, len(drug_samples['ids']))):
                metadata = drug_samples['metadatas'][i]
                doc = drug_samples['documents'][i]
                print(f"\n  Drug {i+1}:")
                print(f"    DIN: {metadata.get('din', 'N/A')}")
                print(f"    Generic: {metadata.get('generic_name', 'N/A')}")
                print(f"    Brand: {metadata.get('brand_name', 'N/A')}")
                print(f"    Text preview: {doc[:150]}...")
        else:
            print("  ❌ No drug embeddings found!")
        
        # Get sample interchangeable group embeddings
        print(f"\n🔄 Sample Interchangeable Group Embeddings:")
        group_samples = collection.get(
            where={"source_type": "odb_interchangeable_group"},
            limit=3,
            include=['documents', 'metadatas']
        )
        
        if group_samples['ids']:
            for i in range(min(3, len(group_samples['ids']))):
                metadata = group_samples['metadatas'][i]
                doc = group_samples['documents'][i]
                print(f"\n  Group {i+1}:")
                print(f"    Generic: {metadata.get('generic_name', 'N/A')}")
                print(f"    Text preview: {doc[:150]}...")
        else:
            print("  ❌ No interchangeable group embeddings found!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n✨ Test complete!")

if __name__ == "__main__":
    test_odb_embeddings()