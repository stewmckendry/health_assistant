#!/usr/bin/env python3
"""
Verify ODB data in SQL and ChromaDB
"""

import sqlite3
import chromadb
from pathlib import Path

def verify_odb_data():
    """Check ODB data ingestion"""
    
    print("🔍 Verifying ODB Data Ingestion")
    print("=" * 60)
    
    # Check SQL Database
    db_path = "data/dr_off_agent/processed/odb_processed_data.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n📊 SQL Database Statistics:")
    
    # Check drugs table
    cursor.execute("SELECT COUNT(*) FROM odb_drugs")
    drug_count = cursor.fetchone()[0]
    print(f"  ✅ Drugs: {drug_count:,}")
    
    # Check interchangeable groups
    cursor.execute("SELECT COUNT(*) FROM odb_interchangeable_groups")
    group_count = cursor.fetchone()[0]
    print(f"  ✅ Interchangeable Groups: {group_count:,}")
    
    # Sample drug records
    cursor.execute("""
        SELECT din, name, generic_name, strength, dosage_form, individual_price, is_lowest_cost
        FROM odb_drugs
        WHERE individual_price IS NOT NULL
        LIMIT 3
    """)
    drugs = cursor.fetchall()
    
    print("\n📝 Sample Drug Records:")
    for drug in drugs:
        print(f"  DIN: {drug[0]}")
        print(f"    Name: {drug[1]}")
        print(f"    Generic: {drug[2]}")
        print(f"    Strength: {drug[3]} {drug[4]}")
        print(f"    Price: ${drug[5]}")
        print(f"    Lowest Cost: {'Yes' if drug[6] else 'No'}")
        print()
    
    # Check ChromaDB
    print("🔍 ChromaDB Vector Store:")
    chroma_path = "data/dr_off_agent/processed/dr_off/chroma"
    client = chromadb.PersistentClient(path=chroma_path)
    
    try:
        # Get ODB collection
        collection = client.get_collection("odb_documents")
        
        # Get collection count
        results = collection.get(limit=1)
        if results and results['ids']:
            # ChromaDB doesn't have a direct count method, so we peek
            print(f"  ✅ ODB collection exists with embeddings")
            
            # Get sample embeddings
            sample = collection.get(
                limit=3,
                include=['documents', 'metadatas']
            )
            
            if sample['ids']:
                print(f"\n📝 Sample Embeddings ({len(sample['ids'])} shown):")
                for i, doc in enumerate(sample['documents']):
                    metadata = sample['metadatas'][i]
                    print(f"\n  Document {i+1}:")
                    print(f"    Type: {metadata.get('source_type', 'N/A')}")
                    print(f"    DIN: {metadata.get('din', 'N/A')}")
                    print(f"    Generic: {metadata.get('generic_name', 'N/A')}")
                    print(f"    Text preview: {doc[:100]}...")
        else:
            print("  ⚠️ ODB collection exists but appears empty")
            
    except Exception as e:
        print(f"  ❌ Could not access ODB collection: {e}")
    
    # Check for PDF chunks
    print("\n📄 PDF Document Chunks:")
    try:
        # Query for PDF chunks
        results = collection.query(
            query_texts=["ODB formulary"],
            n_results=2,
            where={"document_type": "odb_formulary_pdf"}
        )
        
        if results['ids'][0]:
            print(f"  ✅ Found {len(results['ids'][0])} PDF chunks")
        else:
            print("  ℹ️ No PDF chunks found (may not have been ingested)")
            
    except Exception as e:
        print(f"  ℹ️ Could not query PDF chunks: {e}")
    
    conn.close()
    print("\n✨ Verification complete!")

if __name__ == "__main__":
    verify_odb_data()