#!/usr/bin/env python3
"""Test CEP clinical tools retrieval from database."""

import sqlite3
import json
from pathlib import Path


def test_cep_retrieval():
    """Test retrieval of CEP tools from database."""
    
    print("\n" + "="*60)
    print("TESTING CEP CLINICAL TOOLS RETRIEVAL")
    print("="*60 + "\n")
    
    db_path = "data/processed/dr_opa/opa.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Test 1: Get all CEP tools
    print("Test 1: All CEP tools in database")
    print("-" * 40)
    
    cursor.execute("""
        SELECT 
            document_id,
            title,
            source_url,
            effective_date,
            metadata_json
        FROM opa_documents
        WHERE source_org = 'cep'
            AND document_type = 'clinical_tool'
    """)
    
    tools = cursor.fetchall()
    print(f"Found {len(tools)} CEP tools\n")
    
    for doc_id, title, url, date, metadata_json in tools:
        print(f"Tool: {title}")
        print(f"  ID: {doc_id}")
        print(f"  URL: {url}")
        print(f"  Updated: {date}")
        
        # Parse metadata
        try:
            metadata = json.loads(metadata_json)
            category = metadata.get('category', 'unknown')
            features = metadata.get('features', {})
            active_features = [k.replace('has_', '') for k, v in features.items() if v]
            
            print(f"  Category: {category}")
            if active_features:
                print(f"  Features: {', '.join(active_features)}")
            if metadata.get('has_assessment_tools'):
                print(f"  Has assessment tools: Yes")
        except:
            pass
        print()
    
    # Test 2: Search for dementia-related content
    print("\nTest 2: Search for dementia-related content")
    print("-" * 40)
    
    cursor.execute("""
        SELECT DISTINCT
            d.title,
            s.section_heading,
            SUBSTR(s.section_text, 1, 200) as snippet
        FROM opa_documents d
        JOIN opa_sections s ON d.document_id = s.document_id
        WHERE d.source_org = 'cep'
            AND (LOWER(d.title) LIKE '%dementia%' 
                 OR LOWER(s.section_text) LIKE '%dementia%')
        LIMIT 5
    """)
    
    results = cursor.fetchall()
    print(f"Found {len(results)} dementia-related sections\n")
    
    for title, heading, snippet in results:
        print(f"Document: {title}")
        print(f"Section: {heading}")
        print(f"Content: {snippet}...")
        print()
    
    # Test 3: Get overview sections
    print("\nTest 3: Overview sections for CEP tools")
    print("-" * 40)
    
    cursor.execute("""
        SELECT 
            d.title,
            s.section_heading,
            LENGTH(s.section_text) as text_length
        FROM opa_documents d
        JOIN opa_sections s ON d.document_id = s.document_id
        WHERE d.source_org = 'cep'
            AND s.chunk_type = 'parent'
    """)
    
    overviews = cursor.fetchall()
    print(f"Found {len(overviews)} overview sections\n")
    
    for title, heading, length in overviews:
        print(f"Tool: {title}")
        print(f"  Overview: {heading}")
        print(f"  Content length: {length} characters")
    
    # Test 4: Check vector embeddings
    print("\nTest 4: Check vector embeddings")
    print("-" * 40)
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT document_id) as unique_docs,
            chunk_type,
            COUNT(CASE WHEN embedding_id IS NOT NULL THEN 1 END) as with_embeddings
        FROM opa_sections
        WHERE document_id IN (
            SELECT document_id 
            FROM opa_documents 
            WHERE source_org = 'cep'
        )
        GROUP BY chunk_type
    """)
    
    embeddings = cursor.fetchall()
    
    for total, docs, chunk_type, with_embed in embeddings:
        print(f"Chunk type: {chunk_type}")
        print(f"  Total sections: {total}")
        print(f"  Unique documents: {docs}")
        print(f"  With embeddings: {with_embed}")
    
    conn.close()
    
    print("\n" + "="*60)
    print("TEST COMPLETED!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_cep_retrieval()