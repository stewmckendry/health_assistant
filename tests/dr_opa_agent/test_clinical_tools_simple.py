#!/usr/bin/env python3
"""Simple direct test of CEP clinical tools functionality."""

import sqlite3
import json
from pathlib import Path

def test_clinical_tools_simple():
    """Simple test using direct database queries."""
    
    print("\n" + "="*80)
    print("SIMPLE CEP CLINICAL TOOLS DATABASE TEST")
    print("="*80 + "\n")
    
    # Connect to database
    db_path = "data/processed/dr_opa/opa.db"
    if not Path(db_path).exists():
        print(f"❌ Database not found at: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Test 1: Count CEP tools
    print("Test 1: CEP tools overview")
    print("-" * 50)
    
    cursor.execute("SELECT COUNT(*) FROM opa_documents WHERE source_org='cep'")
    doc_count = cursor.fetchone()[0]
    print(f"✓ Total CEP tools: {doc_count}")
    
    cursor.execute("SELECT COUNT(*) FROM opa_sections WHERE document_id IN (SELECT document_id FROM opa_documents WHERE source_org='cep')")
    section_count = cursor.fetchone()[0]
    print(f"✓ Total sections: {section_count}")
    
    cursor.execute("SELECT COUNT(*) FROM opa_sections WHERE embedding_id IS NOT NULL AND document_id IN (SELECT document_id FROM opa_documents WHERE source_org='cep')")
    embedding_count = cursor.fetchone()[0]
    print(f"✓ Sections with embeddings: {embedding_count}")
    print(f"✓ Embedding coverage: {embedding_count/section_count*100:.1f}%")
    
    # Test 2: Sample tools
    print("\n\nTest 2: Sample clinical tools")
    print("-" * 50)
    
    cursor.execute("""
        SELECT title, source_url, effective_date
        FROM opa_documents 
        WHERE source_org='cep' 
        ORDER BY title 
        LIMIT 10
    """)
    
    tools = cursor.fetchall()
    for i, (title, url, date) in enumerate(tools, 1):
        print(f"{i:2d}. {title}")
        print(f"    URL: {url}")
        if date:
            print(f"    Updated: {date}")
        print()
    
    # Test 3: Search capabilities
    print(f"Test 3: Search for key conditions")
    print("-" * 50)
    
    conditions = ["dementia", "diabetes", "opioid", "depression", "anxiety"]
    
    for condition in conditions:
        cursor.execute("""
            SELECT DISTINCT d.title
            FROM opa_documents d
            JOIN opa_sections s ON d.document_id = s.document_id
            WHERE d.source_org = 'cep'
                AND (LOWER(d.title) LIKE ? OR LOWER(s.section_text) LIKE ?)
            LIMIT 3
        """, [f"%{condition.lower()}%", f"%{condition.lower()}%"])
        
        results = cursor.fetchall()
        print(f"'{condition}': {len(results)} tools found")
        for (title,) in results:
            print(f"  - {title}")
    
    # Test 4: Tool features
    print(f"\n\nTest 4: Tool features analysis")
    print("-" * 50)
    
    cursor.execute("""
        SELECT title, metadata_json
        FROM opa_documents 
        WHERE source_org='cep' AND metadata_json IS NOT NULL
        LIMIT 5
    """)
    
    results = cursor.fetchall()
    feature_counts = {}
    
    for title, metadata_json in results:
        print(f"Tool: {title}")
        try:
            metadata = json.loads(metadata_json)
            features = metadata.get('features', {})
            if isinstance(features, dict):
                active_features = [k for k, v in features.items() if v]
                if active_features:
                    print(f"  Features: {', '.join(active_features)}")
                    for feature in active_features:
                        feature_counts[feature] = feature_counts.get(feature, 0) + 1
                else:
                    print("  Features: None specified")
            else:
                print("  Features: Not available")
        except Exception as e:
            print(f"  Features: Error parsing metadata - {e}")
        print()
    
    if feature_counts:
        print("Feature distribution across sampled tools:")
        for feature, count in sorted(feature_counts.items()):
            print(f"  {feature}: {count} tools")
    
    # Test 5: Content verification
    print(f"\n\nTest 5: Sample content verification")
    print("-" * 50)
    
    cursor.execute("""
        SELECT d.title, s.section_heading, s.section_text
        FROM opa_documents d
        JOIN opa_sections s ON d.document_id = s.document_id
        WHERE d.source_org = 'cep' 
            AND LOWER(d.title) LIKE '%dementia%'
            AND s.chunk_type = 'parent'
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    if result:
        title, heading, text = result
        print(f"Sample from: {title}")
        print(f"Section: {heading}")
        print(f"Content preview: {text[:300]}...")
        print(f"Content length: {len(text)} characters")
        
        # Check for clinical content
        clinical_words = ["assessment", "diagnosis", "treatment", "patient", "clinical"]
        found_words = [word for word in clinical_words if word.lower() in text.lower()]
        print(f"Clinical indicators: {', '.join(found_words)}")
    else:
        print("❌ No dementia content found")
    
    # Test 6: Chunk types
    print(f"\n\nTest 6: Chunk distribution")
    print("-" * 50)
    
    cursor.execute("""
        SELECT 
            chunk_type,
            COUNT(*) as total,
            AVG(LENGTH(section_text)) as avg_length
        FROM opa_sections
        WHERE document_id IN (SELECT document_id FROM opa_documents WHERE source_org='cep')
        GROUP BY chunk_type
    """)
    
    for chunk_type, count, avg_length in cursor.fetchall():
        print(f"{chunk_type}: {count} chunks, avg {avg_length:.0f} chars")
    
    conn.close()
    
    print("\n" + "="*80)
    print("✅ SIMPLE DATABASE TEST COMPLETED!")
    print("="*80)
    print(f"Summary: {doc_count} tools, {section_count} sections, {embedding_count} embeddings")
    print("="*80 + "\n")
    
    return True


if __name__ == "__main__":
    success = test_clinical_tools_simple()
    exit(0 if success else 1)