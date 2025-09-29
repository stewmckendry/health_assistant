#!/usr/bin/env python3
"""
Check what metadata is actually stored in ChromaDB for OHIP documents
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
import json

def check_metadata():
    """Check metadata content in ChromaDB"""
    
    print("🔍 Checking Metadata in ChromaDB Collection...")
    chroma_path = 'data/dr_off_agent/processed/dr_off/chroma'
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
    collection = client.get_collection('ohip_documents')
    
    # Get sample documents with different fee codes
    test_codes = ["C122", "W232", "E082"]
    
    for code in test_codes:
        print(f"\n{'='*80}")
        print(f"📋 Checking metadata for code: {code}")
        print('='*80)
        
        results = collection.get(
            where={"fee_code": code},
            include=["documents", "metadatas"],
            limit=2
        )
        
        if results['documents']:
            for i, doc in enumerate(results['documents']):
                print(f"\nDocument {i+1}:")
                print(f"Text: {doc[:150]}...")
                
                metadata = results['metadatas'][i]
                print(f"\nMetadata fields:")
                for key, value in sorted(metadata.items()):
                    print(f"  {key:25} = {value}")
        else:
            print(f"No documents found for {code}")
    
    # Check a few documents to see all available metadata fields
    print(f"\n{'='*80}")
    print("📊 Analyzing all metadata fields across collection:")
    print('='*80)
    
    # Get a larger sample to see all fields
    sample = collection.get(
        limit=100,
        include=["metadatas"]
    )
    
    # Collect all unique metadata keys
    all_keys = set()
    for metadata in sample['metadatas']:
        all_keys.update(metadata.keys())
    
    print(f"\nFound {len(all_keys)} unique metadata fields:")
    for key in sorted(all_keys):
        # Check how many docs have this field
        count = sum(1 for m in sample['metadatas'] if key in m)
        print(f"  {key:30} (present in {count}/{len(sample['metadatas'])} docs)")
    
    # Check SQL database for comparison
    print(f"\n{'='*80}")
    print("📊 Checking SQL Database for comparison:")
    print('='*80)
    
    import sqlite3
    db_path = 'data/dr_off_agent/processed/ohip_processed_data.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\nTables in database: {[t[0] for t in tables]}")
        
        # Check ohip_fee_schedule structure
        cursor.execute("PRAGMA table_info(ohip_fee_schedule)")
        columns = cursor.fetchall()
        print(f"\nColumns in ohip_fee_schedule table:")
        for col in columns:
            print(f"  {col[1]:20} {col[2]}")
        
        # Get sample data
        cursor.execute("""
            SELECT * FROM ohip_fee_schedule 
            WHERE fee_code IN ('C122', 'W232', 'E082')
            LIMIT 5
        """)
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nSample SQL data:")
            col_names = [col[1] for col in columns]
            for row in rows:
                print(f"\n  Fee Code: {row[0]}")
                for i, value in enumerate(row[1:], 1):
                    if value:
                        print(f"    {col_names[i]:20} = {value}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking SQL database: {e}")

if __name__ == "__main__":
    check_metadata()