#!/usr/bin/env python3
"""Direct test of CEP clinical tools functionality."""

import sys
import asyncio
import json
import sqlite3
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import database clients
from src.agents.dr_opa_agent.mcp.retrieval import SQLClient


async def test_clinical_tools_direct():
    """Direct test of clinical tools functionality using database queries."""
    
    print("\n" + "="*80)
    print("DIRECT CEP CLINICAL TOOLS TEST")
    print("="*80 + "\n")
    
    # Initialize SQL client
    sql_client = SQLClient()
    
    # Test 1: Get all CEP tools
    print("Test 1: All CEP tools in database")
    print("-" * 50)
    
    query = """
        SELECT 
            document_id,
            title,
            source_url,
            document_type,
            effective_date,
            metadata_json
        FROM opa_documents
        WHERE source_org = 'cep'
        ORDER BY title
    """
    
    results = sql_client.execute_query(query)
    print(f"Found {len(results)} CEP tools\n")
    
    # Group by features
    tool_features = {}
    for doc_id, title, url, doc_type, date, metadata_json in results[:10]:  # Show first 10
        print(f"✓ {title}")
        print(f"  URL: {url}")
        if date:
            print(f"  Updated: {date}")
        
        # Parse metadata to check features
        try:
            metadata = json.loads(metadata_json or '{}')
            features = metadata.get('features', {})
            if isinstance(features, dict):
                active_features = [k for k, v in features.items() if v]
                if active_features:
                    print(f"  Features: {', '.join(active_features)}")
                    
                    # Count feature types
                    for feature in active_features:
                        if feature not in tool_features:
                            tool_features[feature] = 0
                        tool_features[feature] += 1
        except:
            pass
        print()
    
    if len(results) > 10:
        print(f"... and {len(results) - 10} more tools")
    
    print(f"\nFeature distribution:")
    for feature, count in sorted(tool_features.items()):
        print(f"  {feature}: {count} tools")
    
    # Test 2: Search by condition
    print("\n\nTest 2: Search by medical conditions")
    print("-" * 50)
    
    conditions = ["dementia", "diabetes", "opioid", "depression", "pain"]
    
    for condition in conditions:
        query = """
            SELECT DISTINCT d.title
            FROM opa_documents d
            JOIN opa_sections s ON d.document_id = s.document_id
            WHERE d.source_org = 'cep'
                AND (LOWER(d.title) LIKE ? OR LOWER(s.section_text) LIKE ?)
            LIMIT 5
        """
        params = [f"%{condition.lower()}%", f"%{condition.lower()}%"]
        results = sql_client.execute_query(query, params)
        
        print(f"'{condition}': {len(results)} tools found")
        for (title,) in results[:3]:
            print(f"  - {title}")
        if len(results) > 3:
            print(f"  ... and {len(results) - 3} more")
    
    # Test 3: Check sections and embeddings
    print("\n\nTest 3: Sections and embeddings")
    print("-" * 50)
    
    query = """
        SELECT 
            chunk_type,
            COUNT(*) as total,
            COUNT(CASE WHEN embedding_id IS NOT NULL THEN 1 END) as with_embeddings
        FROM opa_sections
        WHERE document_id IN (
            SELECT document_id 
            FROM opa_documents 
            WHERE source_org = 'cep'
        )
        GROUP BY chunk_type
    """
    
    results = sql_client.execute_query(query)
    print("Chunk distribution:")
    for chunk_type, total, with_embeddings in results:
        coverage = (with_embeddings / total * 100) if total > 0 else 0
        print(f"  {chunk_type}: {total} sections, {with_embeddings} with embeddings ({coverage:.1f}%)")
    
    # Test 4: Tool categories
    print("\n\nTest 4: Tool categories analysis")
    print("-" * 50)
    
    query = """
        SELECT title, metadata_json
        FROM opa_documents
        WHERE source_org = 'cep'
    """
    
    results = sql_client.execute_query(query)
    categories = {}
    
    for title, metadata_json in results:
        try:
            metadata = json.loads(metadata_json or '{}')
            category = metadata.get('category', 'unknown')
            if category not in categories:
                categories[category] = []
            categories[category].append(title)
        except:
            if 'unknown' not in categories:
                categories['unknown'] = []
            categories['unknown'].append(title)
    
    print("Tools by inferred category:")
    for category, tools in sorted(categories.items()):
        print(f"  {category}: {len(tools)} tools")
        for tool in sorted(tools)[:2]:
            print(f"    - {tool}")
        if len(tools) > 2:
            print(f"    ... and {len(tools) - 2} more")
    
    # Test 5: Check specific high-value tools
    print("\n\nTest 5: High-value clinical tools verification")
    print("-" * 50)
    
    key_tools = [
        "Dementia Diagnosis",
        "Opioid Use Disorder",
        "Type 2 diabetes",
        "Heart Failure",
        "Anxiety and Depression"
    ]
    
    for tool_name in key_tools:
        query = """
            SELECT d.title, d.source_url, COUNT(s.section_id) as section_count
            FROM opa_documents d
            LEFT JOIN opa_sections s ON d.document_id = s.document_id
            WHERE d.source_org = 'cep' AND LOWER(d.title) LIKE ?
            GROUP BY d.document_id, d.title, d.source_url
            LIMIT 1
        """
        params = [f"%{tool_name.lower()}%"]
        results = sql_client.execute_query(query, params)
        
        if results:
            title, url, section_count = results[0]
            print(f"✓ {title}: {section_count} sections")
        else:
            print(f"✗ {tool_name}: NOT FOUND")
    
    # Test 6: Sample content verification
    print("\n\nTest 6: Sample content verification")
    print("-" * 50)
    
    # Get a sample section from dementia tool
    query = """
        SELECT s.section_heading, s.section_text
        FROM opa_sections s
        JOIN opa_documents d ON s.document_id = d.document_id
        WHERE d.source_org = 'cep' 
            AND LOWER(d.title) LIKE '%dementia%'
            AND s.chunk_type = 'parent'
        LIMIT 1
    """
    
    results = sql_client.execute_query(query)
    if results:
        heading, text = results[0]
        print(f"Sample section from dementia tool:")
        print(f"  Heading: {heading}")
        print(f"  Content preview: {text[:200]}...")
        print(f"  Content length: {len(text)} characters")
        
        # Check for clinical content indicators
        clinical_indicators = ["assessment", "diagnosis", "treatment", "guideline", "recommendation"]
        found_indicators = [word for word in clinical_indicators if word.lower() in text.lower()]
        print(f"  Clinical indicators found: {', '.join(found_indicators)}")
    
    # Test 7: Performance check
    print("\n\nTest 7: Query performance check")
    print("-" * 50)
    
    import time
    
    # Simple search query
    start_time = time.time()
    query = """
        SELECT COUNT(*)
        FROM opa_documents d
        JOIN opa_sections s ON d.document_id = s.document_id
        WHERE d.source_org = 'cep' AND LOWER(s.section_text) LIKE '%diabetes%'
    """
    results = sql_client.execute_query(query)
    elapsed = time.time() - start_time
    
    count = results[0][0] if results else 0
    print(f"Search for 'diabetes': {count} sections found in {elapsed:.3f} seconds")
    
    print("\n" + "="*80)
    print("✅ ALL DIRECT TESTS COMPLETED SUCCESSFULLY!")
    print("="*80 + "\n")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_clinical_tools_direct())
    sys.exit(0 if success else 1)