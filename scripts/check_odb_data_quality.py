#!/usr/bin/env python3
"""
Check ODB data quality in ChromaDB and SQL
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
import sqlite3
import json

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_odb_chromadb():
    """Check ODB data in ChromaDB"""
    
    print("🔍 Checking ODB Data in ChromaDB...")
    chroma_path = 'data/dr_off_agent/processed/dr_off/chroma'
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
    
    # List all collections to find ODB-related ones
    collections = client.list_collections()
    print(f"\n📚 Available collections:")
    for col in collections:
        print(f"  - {col.name}")
    
    # Check if odb_documents exists
    try:
        collection = client.get_collection('odb_documents')
        doc_count = collection.count()
        print(f"\n✅ Found 'odb_documents' collection with {doc_count} documents")
        
        # Get sample documents
        print("\n📄 Sample ODB documents:")
        sample = collection.get(
            limit=5,
            include=["documents", "metadatas"]
        )
        
        for i, doc in enumerate(sample['documents']):
            print(f"\n--- Document {i+1} ---")
            print(f"Text (first 300 chars): {doc[:300]}...")
            
            metadata = sample['metadatas'][i] if sample['metadatas'] else {}
            print(f"\nMetadata fields:")
            for key, value in sorted(metadata.items()):
                print(f"  {key}: {value}")
        
        # Check metadata fields across collection
        print(f"\n📊 Analyzing metadata fields across collection:")
        larger_sample = collection.get(
            limit=100,
            include=["metadatas"]
        )
        
        all_keys = set()
        for metadata in larger_sample['metadatas']:
            all_keys.update(metadata.keys())
        
        print(f"Found {len(all_keys)} unique metadata fields:")
        for key in sorted(all_keys):
            count = sum(1 for m in larger_sample['metadatas'] if key in m)
            print(f"  {key:30} (present in {count}/{len(larger_sample['metadatas'])} docs)")
            
    except Exception as e:
        print(f"❌ Error accessing 'odb_documents' collection: {e}")

def check_odb_sql():
    """Check ODB data in SQL database"""
    
    print(f"\n{'='*80}")
    print("📊 Checking ODB Data in SQL Database:")
    print('='*80)
    
    db_path = 'data/dr_off_agent/processed/odb_processed_data.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\nTables in ODB database: {[t[0] for t in tables]}")
        
        # Check odb_formulary structure
        cursor.execute("PRAGMA table_info(odb_formulary)")
        columns = cursor.fetchall()
        print(f"\nColumns in odb_formulary table:")
        for col in columns:
            print(f"  {col[1]:25} {col[2]}")
        
        # Get sample data for metformin
        print("\n📋 Sample data for 'metformin':")
        cursor.execute("""
            SELECT * FROM odb_formulary 
            WHERE LOWER(generic_name) LIKE '%metformin%' 
               OR LOWER(brand_name) LIKE '%metformin%'
            LIMIT 5
        """)
        rows = cursor.fetchall()
        col_names = [col[1] for col in columns]
        
        for row in rows:
            print(f"\n  DIN: {row[0]}")
            for i, value in enumerate(row[1:], 1):
                if value and str(value).strip():
                    print(f"    {col_names[i]:25} = {value}")
        
        # Get sample data for atorvastatin
        print("\n📋 Sample data for 'atorvastatin':")
        cursor.execute("""
            SELECT * FROM odb_formulary 
            WHERE LOWER(generic_name) LIKE '%atorvastatin%' 
               OR LOWER(brand_name) LIKE '%atorvastatin%'
            LIMIT 5
        """)
        rows = cursor.fetchall()
        
        for row in rows:
            print(f"\n  DIN: {row[0]}")
            for i, value in enumerate(row[1:], 1):
                if value and str(value).strip():
                    print(f"    {col_names[i]:25} = {value}")
        
        # Check for Limited Use table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%lu%'")
        lu_tables = cursor.fetchall()
        if lu_tables:
            print(f"\nFound Limited Use tables: {[t[0] for t in lu_tables]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking SQL database: {e}")

if __name__ == "__main__":
    check_odb_chromadb()
    check_odb_sql()