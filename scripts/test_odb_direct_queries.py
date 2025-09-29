#!/usr/bin/env python3
"""
Test ODB data with direct SQL and ChromaDB queries using natural clinician language.
Tests both structured SQL queries and semantic vector search.
"""

import sqlite3
import chromadb
import openai
import os
from dotenv import load_dotenv
from typing import Dict, List, Any
import json

# Load environment variables
load_dotenv()

# Natural clinician queries to test
CLINICIAN_QUERIES = [
    # Coverage queries
    "Is Ozempic covered for type 2 diabetes?",
    "Can I prescribe Jardiance for my diabetic patient?",
    "Is metformin on the formulary?",
    
    # Generic/alternative queries
    "What's the cheapest statin that's covered?",
    "Is there a generic for Januvia?",
    "What are the covered alternatives to Lipitor?",
    
    # Specific drug queries
    "Is sitagliptin covered without Limited Use?",
    "What's the cost difference between brand and generic atorvastatin?",
    "Is Tresiba covered for insulin-dependent patients?",
    
    # Complex queries
    "My patient can't afford Januvia, what cheaper alternatives are covered?",
    "Which GLP-1 agonists are on the formulary?",
    "Are SGLT2 inhibitors like empagliflozin covered?"
]

def test_sql_queries():
    """Test direct SQL queries against odb_drugs table"""
    print("=" * 80)
    print("🔍 TESTING SQL QUERIES")
    print("=" * 80)
    
    conn = sqlite3.connect('data/ohip.db')
    cursor = conn.cursor()
    
    # Map clinician terms to SQL searches (using 'name' column for brand names)
    query_mappings = {
        "Ozempic": "SELECT * FROM odb_drugs WHERE LOWER(name) LIKE '%ozempic%' OR LOWER(generic_name) LIKE '%semaglutide%'",
        "Jardiance": "SELECT * FROM odb_drugs WHERE LOWER(name) LIKE '%jardiance%' OR LOWER(generic_name) LIKE '%empagliflozin%'",
        "metformin": "SELECT * FROM odb_drugs WHERE LOWER(generic_name) LIKE '%metformin%'",
        "statin": "SELECT * FROM odb_drugs WHERE LOWER(therapeutic_class) LIKE '%statin%' OR LOWER(generic_name) IN ('atorvastatin', 'simvastatin', 'rosuvastatin', 'pravastatin') ORDER BY individual_price ASC LIMIT 5",
        "Januvia": "SELECT * FROM odb_drugs WHERE LOWER(name) LIKE '%januvia%' OR LOWER(generic_name) LIKE '%sitagliptin%'",
        "Lipitor": "SELECT d1.*, d2.name as alt_brand, d2.generic_name as alt_generic, d2.individual_price as alt_price FROM odb_drugs d1 LEFT JOIN odb_drugs d2 ON d1.interchangeable_group_id = d2.interchangeable_group_id WHERE LOWER(d1.name) LIKE '%lipitor%'",
        "sitagliptin": "SELECT * FROM odb_drugs WHERE LOWER(generic_name) LIKE '%sitagliptin%'",
        "atorvastatin": "SELECT name, generic_name, strength, individual_price, is_lowest_cost FROM odb_drugs WHERE LOWER(generic_name) LIKE '%atorvastatin%' ORDER BY strength, individual_price",
        "Tresiba": "SELECT * FROM odb_drugs WHERE LOWER(name) LIKE '%tresiba%' OR LOWER(generic_name) LIKE '%degludec%'",
        "GLP-1": "SELECT DISTINCT name, generic_name, individual_price FROM odb_drugs WHERE LOWER(therapeutic_class) LIKE '%glp%' OR LOWER(generic_name) IN ('semaglutide', 'liraglutide', 'dulaglutide', 'exenatide')",
        "SGLT2": "SELECT DISTINCT name, generic_name, individual_price FROM odb_drugs WHERE LOWER(therapeutic_class) LIKE '%sglt%' OR LOWER(generic_name) IN ('empagliflozin', 'dapagliflozin', 'canagliflozin')",
        "empagliflozin": "SELECT * FROM odb_drugs WHERE LOWER(generic_name) LIKE '%empagliflozin%'"
    }
    
    for query in CLINICIAN_QUERIES[:3]:  # Test first 3 queries
        print(f"\n📝 Query: {query}")
        
        # Find matching SQL query
        sql_query = None
        for term, sql in query_mappings.items():
            if term.lower() in query.lower():
                sql_query = sql
                break
        
        if sql_query:
            cursor.execute(sql_query)
            results = cursor.fetchall()
            
            if results:
                print(f"  ✅ Found {len(results)} results in SQL")
                # Show first result
                if results[0]:
                    cols = [desc[0] for desc in cursor.description]
                    first_result = dict(zip(cols, results[0]))
                    print(f"  First match: {first_result.get('name', 'N/A')} ({first_result.get('generic_name', 'N/A')})")
                    print(f"    - DIN: {first_result.get('din', 'N/A')}")
                    print(f"    - Price: ${first_result.get('individual_price', 'N/A')}")
                    print(f"    - Lowest cost: {first_result.get('is_lowest_cost', False)}")
            else:
                print("  ❌ No results found in SQL")
        else:
            print("  ⚠️  No SQL mapping for this query")
    
    conn.close()

def test_vector_search():
    """Test semantic search against ChromaDB odb_documents collection"""
    print("\n" + "=" * 80)
    print("🔍 TESTING VECTOR SEARCH (ChromaDB)")
    print("=" * 80)
    
    # Connect to ChromaDB
    chroma_path = "data/dr_off_agent/processed/dr_off/chroma"
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection("odb_documents")
    
    # Get collection stats
    count = collection.count()
    print(f"\n📊 Collection stats: {count} total chunks")
    
    # Initialize OpenAI for embeddings
    openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    for query in CLINICIAN_QUERIES[:3]:  # Test first 3 queries
        print(f"\n📝 Query: {query}")
        
        # Generate embedding for query
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = response.data[0].embedding
        
        # Search ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            include=['documents', 'metadatas', 'distances']
        )
        
        if results['documents'][0]:
            print(f"  ✅ Found {len(results['documents'][0])} vector matches")
            
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0], 
                results['metadatas'][0],
                results['distances'][0]
            )):
                print(f"\n  Match {i+1} (distance: {distance:.3f}):")
                
                # Check if it's a drug chunk or PDF chunk
                if metadata.get('din'):
                    print(f"    Type: Drug embedding")
                    print(f"    DIN: {metadata.get('din', 'N/A')}")
                    print(f"    Generic: {metadata.get('generic_name', 'N/A')}")
                    print(f"    Brand: {metadata.get('brand_name', 'N/A')}")
                    print(f"    Therapeutic: {metadata.get('therapeutic_class', 'N/A')}")
                else:
                    print(f"    Type: PDF chunk")
                    print(f"    Source: {metadata.get('source', 'N/A')}")
                    print(f"    Page: {metadata.get('page_num', 'N/A')}")
                
                # Show text preview
                text_preview = doc[:200] + "..." if len(doc) > 200 else doc
                print(f"    Text: {text_preview}")
        else:
            print("  ❌ No vector matches found")

def test_combined_retrieval():
    """Test how SQL and vector results would be combined"""
    print("\n" + "=" * 80)
    print("🔍 TESTING COMBINED RETRIEVAL (SQL + Vector)")
    print("=" * 80)
    
    # Example: Search for a diabetes medication
    test_query = "Is Jardiance covered for my diabetic patient?"
    print(f"\n📝 Query: {test_query}")
    
    # SQL search
    conn = sqlite3.connect('data/ohip.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT din, name, generic_name, strength, individual_price, is_lowest_cost
        FROM odb_drugs 
        WHERE LOWER(name) LIKE '%jardiance%' 
           OR LOWER(generic_name) LIKE '%empagliflozin%'
        LIMIT 5
    """)
    sql_results = cursor.fetchall()
    conn.close()
    
    print(f"\n  SQL Results: Found {len(sql_results)} drugs")
    if sql_results:
        for row in sql_results[:2]:
            print(f"    - {row[1]} ({row[2]} {row[3]}): ${row[4]}")
    
    # Vector search for context
    chroma_path = "data/dr_off_agent/processed/dr_off/chroma"
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection("odb_documents")
    
    openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=test_query
    )
    query_embedding = response.data[0].embedding
    
    vector_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3,
        where={"$or": [
            {"generic_name": {"$eq": "empagliflozin"}},
            {"brand_name": {"$eq": "JARDIANCE"}}
        ]} if sql_results else None,
        include=['documents', 'metadatas']
    )
    
    print(f"\n  Vector Results: Found {len(vector_results['documents'][0])} contextual matches")
    if vector_results['documents'][0]:
        for i, metadata in enumerate(vector_results['metadatas'][0][:2]):
            if metadata.get('din'):
                print(f"    - Drug context: {metadata.get('generic_name', 'N/A')} - {metadata.get('therapeutic_class', 'N/A')}")
            else:
                print(f"    - Policy context: {metadata.get('source', 'N/A')} p.{metadata.get('page_num', 'N/A')}")
    
    # Combined confidence
    if sql_results and vector_results['documents'][0]:
        print("\n  ✅ HIGH CONFIDENCE: Found in both SQL and vector store")
        print("  📊 Coverage: YES - Drug is in formulary")
    elif sql_results:
        print("\n  ⚠️  MEDIUM CONFIDENCE: Found in SQL only")
        print("  📊 Coverage: LIKELY - Drug found in formulary")
    elif vector_results['documents'][0]:
        print("\n  ⚠️  LOW CONFIDENCE: Found in vector only")
        print("  📊 Coverage: UNCERTAIN - Check policy documents")
    else:
        print("\n  ❌ NO DATA: Drug not found")
        print("  📊 Coverage: UNKNOWN")

def main():
    print("\n" + "🏥 ODB Direct Query Testing 🏥".center(80))
    print("Testing natural clinician queries against SQL and ChromaDB\n")
    
    # Test SQL queries
    test_sql_queries()
    
    # Test vector search
    test_vector_search()
    
    # Test combined retrieval
    test_combined_retrieval()
    
    print("\n" + "=" * 80)
    print("✅ Direct query testing complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()